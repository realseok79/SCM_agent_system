import pytest
import pandas as pd
from unittest.mock import MagicMock
from utils.parser.validation_engine import validate_rows
from utils.parser.exceptions import ValidationPayloadTooLargeError
from models import standardize_region

MAX_VALIDATION_PAYLOAD_BYTES = 2097152

def test_payload_size_limit_exceeded():
    """
    [Rule: MAX_VALIDATION_PAYLOAD_BYTES]
    2MB 초과 페이로드 주입 시 ValidationPayloadTooLargeError 발생 여부를 검증합니다.
    """
    # 2MB를 초과하기 위해 엄청나게 긴 더미 텍스트를 가진 데이터프레임 구성
    long_text = "A" * (2 * 1024 * 1024 + 1000)
    df = pd.DataFrame([{
        "region_code": "KR-11",
        "product_name": "SemiConductor_A",
        "date": "2026-05-20",
        "quantity": 100.0,
        "dummy_col": long_text
    }])
    
    mapping = {
        "region_code": "region_code",
        "product_name": "product_name",
        "date": "date",
        "quantity": "quantity",
        "dummy_col": "dummy_col"
    }
    
    with pytest.raises(ValidationPayloadTooLargeError) as exc_info:
        validate_rows(df, mapping, company_id="COMP-A")
    
    assert "exceeds maximum limit of 2MB" in str(exc_info.value)

def test_invalid_region_code_value_error():
    """
    [standardize_region ValueError 분기 검증]
    매핑 불가능하고 유효하지 않은 지역명이 들어왔을 때 ValueError 발생 검증.
    """
    with pytest.raises(ValueError):
        standardize_region("INVALID_REGION_XYZ_999")
