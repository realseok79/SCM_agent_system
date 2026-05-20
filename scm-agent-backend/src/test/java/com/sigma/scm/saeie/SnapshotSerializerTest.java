package com.sigma.scm.saeie;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.zip.GZIPOutputStream;

import static org.junit.jupiter.api.Assertions.*;

public class SnapshotSerializerTest {

    private SnapshotSerializer serializer;

    @BeforeEach
    public void setUp() {
        serializer = new SnapshotSerializer();
    }

    @Test
    public void testNormalSerializationAndDeserialization() throws Exception {
        List<Map<String, Object>> original = new ArrayList<>();
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("index", 1);
        row.put("product", "Mask");
        original.add(row);

        byte[] compressed = serializer.serializeSnapshot(original);
        assertNotNull(compressed);
        assertTrue(compressed.length > 0);

        List<Map<String, Object>> recovered = serializer.deserializeSnapshot(compressed);
        assertEquals(1, recovered.size());
        assertEquals("Mask", recovered.get(0).get("product"));
    }

    @Test
    public void testZipBombPrevention() throws IOException {
        // Create an extremely large redundant stream that compresses well but expands to > 10MB
        byte[] largeData = new byte[11 * 1024 * 1024]; // 11MB
        Arrays.fill(largeData, (byte) 'A');

        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        try (GZIPOutputStream gzos = new GZIPOutputStream(bos)) {
            gzos.write(largeData);
        }
        byte[] zipBomb = bos.toByteArray();

        assertThrows(SaeieException.SnapshotDecodeException.class, () -> {
            serializer.deserializeSnapshot(zipBomb);
        });
    }

    @Test
    public void testTrailingGarbageRejection() throws IOException {
        List<Map<String, Object>> original = new ArrayList<>();
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("val", "OK");
        original.add(row);

        byte[] compressed = serializer.serializeSnapshot(original);
        
        // Append trailing garbage byte
        byte[] polluted = new byte[compressed.length + 5];
        System.arraycopy(compressed, 0, polluted, 0, compressed.length);
        polluted[compressed.length] = 0x12; // arbitrary junk byte

        assertThrows(SaeieException.SnapshotDecodeException.class, () -> {
            serializer.deserializeSnapshot(polluted);
        });
    }
}
