# tests/test_schema_registry.py
from utils.schema_registry import SCHEMA_REGISTRY, calculate_registry_checksum

def test_schema_registry_has_required_columns():
    """필수 컬럼 4개가 가중치 1.0으로 등록되어 있는지 검증"""
    required = ["region_code", "product_name", "date", "quantity"]
    for col in required:
        assert col in SCHEMA_REGISTRY
        assert SCHEMA_REGISTRY[col]["required"] is True
        assert SCHEMA_REGISTRY[col]["alias_weight"] == 1.0

def test_schema_registry_has_optional_columns():
    """선택 컬럼 2개가 가중치 0.8로 등록되어 있는지 검증"""
    optional = ["company_id", "warehouse_code"]
    for col in optional:
        assert col in SCHEMA_REGISTRY
        assert SCHEMA_REGISTRY[col]["required"] is False
        assert SCHEMA_REGISTRY[col]["alias_weight"] == 0.8

def test_calculate_registry_checksum_deterministic():
    """체크섬 결과가 결정론적(동일 입력 → 동일 해시)인지 검증"""
    checksum_1 = calculate_registry_checksum()
    checksum_2 = calculate_registry_checksum()
    assert checksum_1 == checksum_2
    assert isinstance(checksum_1, str)
    assert len(checksum_1) == 64  # SHA256 hex digest length
