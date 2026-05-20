# tests/test_canonical_checksum.py
import pytest
import unicodedata
from utils.parser.snapshot_utils import (
    serialize_snapshot,
    deserialize_snapshot,
    canonicalize_value
)
from utils.parser.semantic_mapper import canonicalize_header

def test_float_rounding_tie_breaker():
    """Verify that floats are rounded to exactly 8 decimal places in serialized snapshots"""
    # 9번째 소수점이 5 미만인 두 수를 사용하여 동일한 8자리 반올림 결과를 보장합니다.
    # round(12.345678901, 8) = 12.3456789 (9번째 자리 '1' → 버림)
    # round(12.345678904, 8) = 12.3456789 (9번째 자리 '4' → 버림)
    payload_1 = [
        {
            "source_row_index": 0,
            "standardized_values": {"quantity": 12.345678901, "product_name": "Mask"},
            "raw_row_data": {"qty": "original"},
            "validation_errors": []
        }
    ]
    payload_2 = [
        {
            "source_row_index": 0,
            "standardized_values": {"quantity": 12.345678904, "product_name": "Mask"},
            "raw_row_data": {"qty": "original"},
            "validation_errors": []
        }
    ]
    
    bytes_1 = serialize_snapshot(payload_1)
    bytes_2 = serialize_snapshot(payload_2)
    
    # 두 float 모두 round(x, 8) = 12.3456789 이므로 압축 바이트가 동일해야 합니다.
    assert bytes_1 == bytes_2
    
    # 역직렬화 후 반올림 결과 확인
    deserialized = deserialize_snapshot(bytes_1)
    assert deserialized[0]["standardized_values"]["quantity"] == 12.3456789

def test_canonicalize_value_float_precision():
    """Verify canonicalize_value rounds float to 8 decimal places"""
    # round(12.345678901, 8) = 12.3456789 (9번째 자리 '1' → 버림)
    result = canonicalize_value(12.345678901)
    assert result == 12.3456789
    
    # round(12.345678904, 8) = 12.3456789 (9번째 자리 '4' → 버림)
    result2 = canonicalize_value(12.345678904)
    assert result2 == 12.3456789
    
    assert canonicalize_value(result) == canonicalize_value(result2)
    
    # round(12.345678909, 8) = 12.34567891 (9번째 자리 '9' → 올림)
    result3 = canonicalize_value(12.345678909)
    assert result3 == 12.34567891

def test_unicode_nfc_normalization():
    """Verify that all strings in serialized snapshots are NFC normalized"""
    # Create NFD decomposed Hangul (각)
    nfd_string = unicodedata.normalize('NFD', '각')
    assert unicodedata.is_normalized('NFC', nfd_string) is False
    
    payload = [
        {
            "source_row_index": 0,
            "standardized_values": {"product_name": nfd_string, "quantity": 100.0},
            "raw_row_data": {"품목": nfd_string},
            "validation_errors": []
        }
    ]
    
    compressed_bytes = serialize_snapshot(payload)
    deserialized = deserialize_snapshot(compressed_bytes)
    
    resolved_str = deserialized[0]["standardized_values"]["product_name"]
    assert unicodedata.is_normalized('NFC', resolved_str) is True
    assert resolved_str == '각'

def test_canonicalize_header_caching():
    """Verify that canonicalize_header returns clean alphanumeric values and is pure stateless"""
    raw_header_1 = "  Product-Name__Title  "
    raw_header_2 = "product_name_title"
    
    clean_1 = canonicalize_header(raw_header_1)
    clean_2 = canonicalize_header(raw_header_2)
    
    assert clean_1 == "productnametitle"
    assert clean_2 == "productnametitle"
    assert clean_1 == clean_2
