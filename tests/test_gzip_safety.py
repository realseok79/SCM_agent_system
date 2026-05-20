# tests/test_gzip_safety.py
import pytest
import gzip
import zlib
from utils.parser.snapshot_utils import deserialize_snapshot
from utils.parser.exceptions import SnapshotDecodeError

def test_gzip_bomb_protection():
    """Verify that deflating to > 10MB triggers SnapshotDecodeError (Zip Bomb Guard)"""
    # Create highly compressible dummy string (11MB of 'A')
    large_data = b"A" * 11000000
    compressed_bytes = gzip.compress(large_data)
    
    # Restoring should fail immediately once it breaches the 10MB safety ceiling
    with pytest.raises(SnapshotDecodeError) as exc:
        deserialize_snapshot(compressed_bytes)
    # 실제 구현체의 에러 메시지: "Decompressed payload size exceeded limit of 10485760 bytes."
    assert "exceeded limit" in str(exc.value).lower()

def test_gzip_concatenation_attack_protection():
    """Verify that multiple gzip member streams are blocked (Gzip Concatenation Guard)"""
    # Create two separate gzip members
    member_1 = gzip.compress(b'[{"source_row_index":0}]')
    member_2 = gzip.compress(b'[{"source_row_index":1}]')
    
    # Concatenate them (standard multi-member gzip stream)
    concatenated_bytes = member_1 + member_2
    
    # Decompression should block multi-member streams to prevent concatenation attacks
    with pytest.raises(SnapshotDecodeError) as exc:
        deserialize_snapshot(concatenated_bytes)
    # 실제 구현체의 에러 메시지: "Multi-member gzip stream or trailing garbage detected (concatenation attack)."
    assert "concatenation attack" in str(exc.value).lower()

def test_gzip_trailing_garbage_protection():
    """Verify that trailing garbage data after a valid gzip stream is blocked"""
    valid_gzip = gzip.compress(b'[{"source_row_index":0}]')
    corrupted_bytes = valid_gzip + b"GARBAGE_DATA"
    
    with pytest.raises(SnapshotDecodeError) as exc:
        deserialize_snapshot(corrupted_bytes)
    # 실제 구현체의 에러 메시지: "Multi-member gzip stream or trailing garbage detected (concatenation attack)."
    assert "concatenation attack" in str(exc.value).lower()
