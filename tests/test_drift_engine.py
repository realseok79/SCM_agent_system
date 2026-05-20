# tests/test_drift_engine.py
import pytest
from utils.parser.drift_engine import calculate_drift_score, validate_drift
from utils.parser.exceptions import HeaderDriftError

def test_calculate_drift_score_perfect_match():
    """모든 표준 컬럼이 매핑된 경우 DriftScore = 0.0"""
    mapped = ["region_code", "product_name", "date", "quantity", "company_id", "warehouse_code"]
    score = calculate_drift_score(mapped)
    assert score == 0.0

def test_calculate_drift_score_partial_match():
    """일부만 매핑된 경우 DriftScore > 0"""
    mapped = ["region_code", "product_name"]
    score = calculate_drift_score(mapped)
    assert score > 0.0
    assert score <= 1.0

def test_calculate_drift_score_with_none_values():
    """None 값(미매핑 컬럼)은 A_effective에서 제외"""
    mapped = ["region_code", "product_name", None, None, "date", "quantity"]
    score = calculate_drift_score(mapped)
    # A_effective = {region_code, product_name, date, quantity}, B = 6개 표준 컬럼
    # symmetric_difference = {company_id, warehouse_code}
    # DriftScore = 2 / max(4, 6, 1) = 2/6 ≈ 0.333...
    assert 0.3 < score < 0.4

def test_calculate_drift_score_empty():
    """매핑이 전혀 없는 경우 DriftScore 계산"""
    mapped = [None, None, None]
    score = calculate_drift_score(mapped)
    assert score == 1.0  # |{} Δ B| / max(0, 6, 1) = 6/6 = 1.0

def test_validate_drift_passes():
    """정상 범위 내 DriftScore + unknown_cols <= 5 시 정상 통과"""
    mapped = ["region_code", "product_name", "date", "quantity", "company_id", "warehouse_code"]
    score = validate_drift(mapped, unknown_cols_count=0)
    assert score == 0.0

def test_validate_drift_unknown_cols_exceed():
    """unknown_cols_count > 5 시 HeaderDriftError"""
    mapped = ["region_code", "product_name", "date", "quantity"]
    with pytest.raises(HeaderDriftError) as exc:
        validate_drift(mapped, unknown_cols_count=6)
    assert "unknown columns count" in str(exc.value).lower()

def test_validate_drift_score_exceed():
    """DriftScore > 0.5 시 HeaderDriftError"""
    mapped = [None, None, None]  # DriftScore = 1.0
    with pytest.raises(HeaderDriftError) as exc:
        validate_drift(mapped, unknown_cols_count=0)
    assert "drift score" in str(exc.value).lower()
