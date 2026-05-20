# tests/test_snapshot_utils_extended.py
import pytest
import math
import zlib
import gzip
from utils.parser.snapshot_utils import (
    canonicalize_value,
    decompress_snapshot,
    serialize_snapshot,
    deserialize_snapshot
)
from utils.parser.exceptions import SnapshotDecodeError

def test_canonicalize_value_nan_inf():
    """canonicalize_value가 float NaN 또는 Inf를 만났을 때 ValueError가 발생하는지 검증"""
    with pytest.raises(ValueError) as exc_info:
        canonicalize_value(float('nan'))
    assert "NaN or Inf is not allowed" in str(exc_info.value)
    
    with pytest.raises(ValueError) as exc_info:
        canonicalize_value(float('inf'))
    assert "NaN or Inf is not allowed" in str(exc_info.value)

def test_decompress_snapshot_success():
    """정상적으로 압축된 바이너리가 zlib decompress 성공 경로로 잘 복원되는지 검증"""
    data = b"Hello, SCM SAEIE!"
    compressed = gzip.compress(data)
    assert decompress_snapshot(compressed) == data

def test_decompress_snapshot_incomplete_stream():
    """불완전한 gzip 압축 바이트스트림이 전달되었을 때 Incomplete gzip compressed stream 예외가 발생하는지 검증"""
    data = b"Hello, SCM SAEIE!"
    compressed = gzip.compress(data)
    # 뒤의 일부 바이트를 잘라내어 강제로 불완전하게 만듦
    incomplete = compressed[:-5]
    with pytest.raises(SnapshotDecodeError) as exc_info:
        decompress_snapshot(incomplete)
    assert "Incomplete gzip compressed stream" in str(exc_info.value)

def test_decompress_snapshot_trailing_garbage():
    """gzip 스트림 뒤에 악의적으로 쓰레기 바이트가 덧붙여졌을 때 (concatenation attack) 감지 및 차단 검증"""
    data = b"Hello, SCM SAEIE!"
    compressed = gzip.compress(data)
    # 뒤에 0이 아닌 쓰레기 데이터 추가
    malicious = compressed + b"\x01\x02\x03"
    with pytest.raises(SnapshotDecodeError) as exc_info:
        decompress_snapshot(malicious)
    assert "Multi-member gzip stream or trailing garbage detected" in str(exc_info.value)

def test_serialize_deserialize_roundtrip():
    """serialize_snapshot -> deserialize_snapshot 골든 라운드트립 검증"""
    payload = [
        {"item_name": "SemiConducor_A", "quantity": 10.559999999, "nested": {"val": 1.0}}
    ]
    compressed = serialize_snapshot(payload)
    restored = deserialize_snapshot(compressed)
    
    # 8자리 반올림 및 정규화된 형태 확인
    assert restored[0]["quantity"] == 10.56
    assert restored[0]["item_name"] == "SemiConducor_A"
