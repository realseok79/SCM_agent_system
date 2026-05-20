package com.sigma.scm.saeie;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import org.springframework.stereotype.Component;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.nio.charset.StandardCharsets;
import java.text.Normalizer;
import java.util.*;
import java.util.zip.GZIPInputStream;
import java.util.zip.GZIPOutputStream;

@Component
public class SnapshotSerializer {

    private final ObjectMapper objectMapper;

    public SnapshotSerializer() {
        this.objectMapper = new ObjectMapper();
        this.objectMapper.configure(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS, true);
    }

    public static String canonicalizeKey(String key) {
        if (key == null) return "";
        return Normalizer.normalize(key, Normalizer.Form.NFC);
    }

    @SuppressWarnings("unchecked")
    public static Object canonicalizeValue(Object val) {
        if (val == null) {
            return null;
        }
        if (val instanceof String) {
            return Normalizer.normalize((String) val, Normalizer.Form.NFC);
        } else if (val instanceof Double || val instanceof Float) {
            double d = ((Number) val).doubleValue();
            if (Double.isNaN(d) || Double.isInfinite(d)) {
                throw new IllegalArgumentException("NaN or Inf is not allowed in canonical serialization.");
            }
            return BigDecimal.valueOf(d).setScale(8, RoundingMode.HALF_UP).doubleValue();
        } else if (val instanceof Map) {
            Map<Object, Object> source = (Map<Object, Object>) val;
            Map<String, Object> sorted = new TreeMap<>();
            for (Map.Entry<Object, Object> entry : source.entrySet()) {
                String k = canonicalizeKey(String.valueOf(entry.getKey()));
                sorted.put(k, canonicalizeValue(entry.getValue()));
            }
            return sorted;
        } else if (val instanceof List) {
            List<Object> source = (List<Object>) val;
            List<Object> canonicalized = new ArrayList<>();
            for (Object item : source) {
                canonicalized.add(canonicalizeValue(item));
            }
            return canonicalized;
        }
        return val;
    }

    public byte[] serializeSnapshot(List<Map<String, Object>> payloadList) throws IOException {
        Object canonicalized = canonicalizeValue(payloadList);
        String json = objectMapper.writeValueAsString(canonicalized);
        byte[] rawBytes = json.getBytes(StandardCharsets.UTF_8);

        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        try (GZIPOutputStream gzos = new GZIPOutputStream(bos) {
            {
                this.def.setLevel(9); // Level 9 Compression
            }
        }) {
            gzos.write(rawBytes);
        }
        return bos.toByteArray();
    }

    public List<Map<String, Object>> deserializeSnapshot(byte[] compressedBytes) throws IOException {
        byte[] decompressedBytes = decompressSnapshot(compressedBytes);
        String json = new String(decompressedBytes, StandardCharsets.UTF_8);
        
        try {
            return objectMapper.readValue(json, new TypeReference<List<Map<String, Object>>>() {});
        } catch (Exception e) {
            throw new SaeieException.SnapshotDecodeException("Failed to parse decompressed snapshot JSON: " + e.getMessage());
        }
    }

    private byte[] decompressSnapshot(byte[] compressedBytes) throws IOException {
        int MAX_DECOMPRESSED_SIZE_BYTES = 10485760; // 10MB limit

        if (compressedBytes.length < 18) { // 10 bytes header + 8 bytes trailer
            throw new SaeieException.SnapshotDecodeException("Compressed data is too short to be a valid GZIP stream.");
        }
        if ((compressedBytes[0] & 0xFF) != 0x1F || (compressedBytes[1] & 0xFF) != 0x8B) {
            throw new SaeieException.SnapshotDecodeException("Invalid GZIP magic number.");
        }
        if (compressedBytes[2] != 8) {
            throw new SaeieException.SnapshotDecodeException("Unsupported GZIP compression method.");
        }

        java.util.zip.Inflater inflater = new java.util.zip.Inflater(true);
        inflater.setInput(compressedBytes, 10, compressedBytes.length - 10);

        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        byte[] buffer = new byte[65536];
        int totalBytesDecompressed = 0;

        try {
            while (!inflater.finished()) {
                int count = inflater.inflate(buffer);
                if (count == 0) {
                    if (inflater.needsInput()) {
                        throw new SaeieException.SnapshotDecodeException("Truncated GZIP stream.");
                    }
                    break;
                }
                totalBytesDecompressed += count;
                if (totalBytesDecompressed > MAX_DECOMPRESSED_SIZE_BYTES) {
                    throw new SaeieException.SnapshotDecodeException(
                        "Decompressed payload size exceeded limit of " + MAX_DECOMPRESSED_SIZE_BYTES + " bytes."
                    );
                }
                bos.write(buffer, 0, count);
            }

            long compressedBytesRead = inflater.getBytesRead();
            long expectedGzipSize = 10 + compressedBytesRead + 8;

            if (compressedBytes.length > expectedGzipSize) {
                for (int i = (int) expectedGzipSize; i < compressedBytes.length; i++) {
                    if (compressedBytes[i] != 0) {
                        throw new SaeieException.SnapshotDecodeException(
                            "Multi-member gzip stream or trailing garbage detected (concatenation attack)."
                        );
                    }
                }
            }

            return bos.toByteArray();
        } catch (java.util.zip.DataFormatException e) {
            throw new SaeieException.SnapshotDecodeException("Zlib decompression failed: " + e.getMessage());
        } finally {
            inflater.end();
        }
    }
}
