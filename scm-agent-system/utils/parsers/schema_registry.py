# utils/schema_registry.py
import json
import hashlib

SCHEMA_REGISTRY = {
    # 필수 컬럼 (Required)
    "region_code": {"required": True, "alias_weight": 1.0},
    "product_name": {"required": True, "alias_weight": 1.0},
    "date": {"required": True, "alias_weight": 1.0},
    "quantity": {"required": True, "alias_weight": 1.0},
    # 선택 컬럼 (Optional)
    "company_id": {"required": False, "alias_weight": 0.8},
    "warehouse_code": {"required": False, "alias_weight": 0.8}
}

def calculate_registry_checksum() -> str:
    """
    레지스트리 딕셔너리를 Canonical JSON 직렬화한 후 UTF-8 인코딩을 거쳐 SHA256 체크섬을 결정론적으로 계산합니다.
    """
    serialized = json.dumps(SCHEMA_REGISTRY, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
