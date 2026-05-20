# utils/parser/snapshot_utils.py
import json
import gzip
import zlib
import math
import unicodedata
from utils.parser.exceptions import SnapshotDecodeError

def canonicalize_key(key: str) -> str:
    """UTF-8 NFC Normalization on string key"""
    return unicodedata.normalize('NFC', str(key))

def canonicalize_value(val):
    """
    Recursively canonicalize:
    1. Float precision: round to 8 decimal places (reject NaN/Inf)
    2. String value: NFC Normalization
    3. Nested dicts/lists
    """
    if isinstance(val, str):
        return unicodedata.normalize('NFC', val)
    elif isinstance(val, float):
        if math.isnan(val) or math.isinf(val):
            raise ValueError("NaN or Inf is not allowed in canonical serialization.")
        return round(val, 8)
    elif isinstance(val, dict):
        return {canonicalize_key(k): canonicalize_value(v) for k, v in val.items()}
    elif isinstance(val, list):
        return [canonicalize_value(item) for item in val]
    return val

def decompress_snapshot(compressed_bytes: bytes) -> bytes:
    """
    Safe Gzip decompression:
    1. Limit max decompressed size to 10MB (MAX_DECOMPRESSED_SIZE_BYTES)
    2. Read sequentially in 64KB chunks to prevent Zip bomb
    3. Multi-member / trailing data protection (concatenation attack defense)
    """
    MAX_DECOMPRESSED_SIZE_BYTES = 10485760  # 10MB
    CHUNK_SIZE = 65536  # 64KB
    
    dobj = zlib.decompressobj(16 + zlib.MAX_WBITS)
    decompressed_buffer = bytearray()
    
    offset = 0
    total_len = len(compressed_bytes)
    
    while offset < total_len:
        chunk = compressed_bytes[offset:offset + CHUNK_SIZE]
        offset += CHUNK_SIZE
        
        try:
            decompressed_chunk = dobj.decompress(chunk)
        except zlib.error as e:
            raise SnapshotDecodeError(f"Zlib decompression failed: {e}")
            
        decompressed_buffer.extend(decompressed_chunk)
        
        if len(decompressed_buffer) > MAX_DECOMPRESSED_SIZE_BYTES:
            raise SnapshotDecodeError(
                f"Decompressed payload size exceeded limit of {MAX_DECOMPRESSED_SIZE_BYTES} bytes."
            )
            
        if dobj.eof:
            # Reached end of the first gzip member.
            # Any remaining bytes must be strictly verified.
            remaining_in_chunk = chunk[len(chunk) - len(dobj.unconsumed_tail):] if dobj.unconsumed_tail else b""
            trailing_data = remaining_in_chunk + compressed_bytes[offset:]
            if dobj.unused_data or (trailing_data and any(b != 0 for b in trailing_data)):
                raise SnapshotDecodeError("Multi-member gzip stream or trailing garbage detected (concatenation attack).")
            break
    else:
        if not dobj.eof:
            raise SnapshotDecodeError("Incomplete gzip compressed stream.")
            
    return bytes(decompressed_buffer)

def serialize_snapshot(payload_list: list[dict]) -> bytes:
    """Canonicalize, serialize to JSON, and compress using standard gzip (single member)"""
    canonicalized = canonicalize_value(payload_list)
    serialized_str = json.dumps(canonicalized, sort_keys=True, ensure_ascii=False)
    return gzip.compress(serialized_str.encode('utf-8'), compresslevel=9)

def deserialize_snapshot(compressed_bytes: bytes) -> list[dict]:
    """Decompress safely and load JSON payload list"""
    decompressed_bytes = decompress_snapshot(compressed_bytes)
    try:
        return json.loads(decompressed_bytes.decode('utf-8'))
    except json.JSONDecodeError as e:
        raise SnapshotDecodeError(f"Failed to parse decompressed snapshot JSON: {e}")
