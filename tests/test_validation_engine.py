# tests/test_validation_engine.py
import pytest
import pandas as pd
from datetime import datetime, timedelta
from utils.parser.validation_engine import validate_rows, parse_date
from utils.parser.exceptions import ValidationPayloadTooLargeError

def make_df_and_mapping(rows_data: list[dict], columns=None):
    """Helper to build a DataFrame and mapping for validate_rows"""
    if columns is None:
        columns = ["지점", "상품명", "수량", "날짜"]
    df = pd.DataFrame(rows_data, columns=columns)
    mapping = {
        "지점": "region_code",
        "상품명": "product_name",
        "수량": "quantity",
        "날짜": "date"
    }
    return df, mapping

def test_parse_date_iso_format():
    """ISO-8601 표준 날짜 문자열 파싱 검증"""
    dt = parse_date("2026-05-19")
    assert dt.year == 2026
    assert dt.month == 5
    assert dt.day == 19

def test_parse_date_slash_format():
    """슬래시 구분 날짜 포맷 파싱 검증"""
    dt = parse_date("2026/05/19")
    assert dt.year == 2026
    assert dt.month == 5
    assert dt.day == 19

def test_parse_date_datetime_object():
    """datetime 객체 직접 전달 시 파싱 검증"""
    now = datetime.now()
    dt = parse_date(now)
    assert dt.year == now.year

def test_parse_date_timestamp():
    """Pandas Timestamp 객체 파싱 검증"""
    ts = pd.Timestamp("2026-05-19")
    dt = parse_date(ts)
    assert dt.year == 2026

def test_parse_date_invalid():
    """파싱 불가 문자열에 대한 ValueError 검증"""
    with pytest.raises(ValueError):
        parse_date("not_a_date")

def test_validate_rows_all_valid():
    """모든 행이 정상일 때 CRITICAL/ERROR 없이 통과"""
    df, mapping = make_df_and_mapping([
        {"지점": "서울", "상품명": "마스크", "수량": 100, "날짜": "2026-05-19"},
        {"지점": "부산", "상품명": "손소독제", "수량": 200, "날짜": "2026-05-19"}
    ])
    payload, has_critical, has_error, has_warning = validate_rows(df, mapping, "COMP_A")
    
    assert len(payload) == 2
    assert has_critical is False
    assert has_error is False

def test_validate_rows_missing_region():
    """지역 컬럼 값이 비어있을 때 CRITICAL 검증"""
    df, mapping = make_df_and_mapping([
        {"지점": "", "상품명": "마스크", "수량": 100, "날짜": "2026-05-19"}
    ])
    payload, has_critical, has_error, has_warning = validate_rows(df, mapping, "COMP_A")
    
    assert has_critical is True
    assert any(e["severity"] == "CRITICAL" for e in payload[0]["validation_errors"])

def test_validate_rows_missing_product():
    """상품명 컬럼 값이 비어있을 때 CRITICAL 검증"""
    df, mapping = make_df_and_mapping([
        {"지점": "서울", "상품명": "", "수량": 100, "날짜": "2026-05-19"}
    ])
    payload, has_critical, has_error, has_warning = validate_rows(df, mapping, "COMP_A")
    
    assert has_critical is True

def test_validate_rows_missing_date():
    """날짜 컬럼 값이 비어있을 때 CRITICAL 검증"""
    df, mapping = make_df_and_mapping([
        {"지점": "서울", "상품명": "마스크", "수량": 100, "날짜": ""}
    ])
    payload, has_critical, has_error, has_warning = validate_rows(df, mapping, "COMP_A")
    
    assert has_critical is True

def test_validate_rows_invalid_date_format():
    """날짜 파싱 실패 시 CRITICAL 검증"""
    df, mapping = make_df_and_mapping([
        {"지점": "서울", "상품명": "마스크", "수량": 100, "날짜": "abc-def-ghi"}
    ])
    payload, has_critical, has_error, has_warning = validate_rows(df, mapping, "COMP_A")
    
    assert has_critical is True
    assert any("parse date" in e["message"].lower() for e in payload[0]["validation_errors"])

def test_validate_rows_negative_quantity():
    """음수 수량 시 ERROR 등급 검증"""
    df, mapping = make_df_and_mapping([
        {"지점": "서울", "상품명": "마스크", "수량": -50, "날짜": "2026-05-19"}
    ])
    payload, has_critical, has_error, has_warning = validate_rows(df, mapping, "COMP_A")
    
    assert has_error is True
    assert any(e["severity"] == "ERROR" and "negative" in e["message"].lower() for e in payload[0]["validation_errors"])

def test_validate_rows_excessive_quantity():
    """1,000,000 이상 수량 시 ERROR 등급 검증"""
    df, mapping = make_df_and_mapping([
        {"지점": "서울", "상품명": "마스크", "수량": 2000000, "날짜": "2026-05-19"}
    ])
    payload, has_critical, has_error, has_warning = validate_rows(df, mapping, "COMP_A")
    
    assert has_error is True
    assert any("exceeds limit" in e["message"].lower() for e in payload[0]["validation_errors"])

def test_validate_rows_fractional_quantity_warning():
    """소수점 수량 시 WARNING 등급 + 자동 반올림 검증"""
    df, mapping = make_df_and_mapping([
        {"지점": "서울", "상품명": "마스크", "수량": 10.7, "날짜": "2026-05-19"}
    ])
    payload, has_critical, has_error, has_warning = validate_rows(df, mapping, "COMP_A")
    
    assert has_warning is True
    assert payload[0]["standardized_values"]["quantity"] == 11.0

def test_validate_rows_future_date_error():
    """1년 초과 미래 날짜 시 ERROR 등급 검증"""
    future = (datetime.now() + timedelta(days=400)).strftime("%Y-%m-%d")
    df, mapping = make_df_and_mapping([
        {"지점": "서울", "상품명": "마스크", "수량": 100, "날짜": future}
    ])
    payload, has_critical, has_error, has_warning = validate_rows(df, mapping, "COMP_A")
    
    assert has_error is True
    assert any("future" in e["message"].lower() for e in payload[0]["validation_errors"])

def test_validate_rows_old_date_warning():
    """5년 초과 과거 날짜 시 WARNING 등급 검증"""
    old_date = (datetime.now() - timedelta(days=2000)).strftime("%Y-%m-%d")
    df, mapping = make_df_and_mapping([
        {"지점": "서울", "상품명": "마스크", "수량": 100, "날짜": old_date}
    ])
    payload, has_critical, has_error, has_warning = validate_rows(df, mapping, "COMP_A")
    
    assert has_warning is True
    assert any("older than 5 years" in e["message"].lower() for e in payload[0]["validation_errors"])

def test_validate_rows_invalid_quantity_string():
    """수량 필드에 문자열 유입 시 CRITICAL 검증"""
    df, mapping = make_df_and_mapping([
        {"지점": "서울", "상품명": "마스크", "수량": "abc", "날짜": "2026-05-19"}
    ])
    payload, has_critical, has_error, has_warning = validate_rows(df, mapping, "COMP_A")
    
    assert has_critical is True
    assert any("cast" in e["message"].lower() for e in payload[0]["validation_errors"])

def test_validate_rows_null_quantity():
    """수량 필드가 null일 때 CRITICAL 검증"""
    df, mapping = make_df_and_mapping([
        {"지점": "서울", "상품명": "마스크", "수량": None, "날짜": "2026-05-19"}
    ])
    payload, has_critical, has_error, has_warning = validate_rows(df, mapping, "COMP_A")
    
    assert has_critical is True

def test_validate_rows_missing_required_mapping():
    """매핑에 필수 컬럼이 없을 때 CRITICAL 검증"""
    df = pd.DataFrame([{"지점": "서울", "상품명": "마스크"}])
    mapping = {"지점": "region_code", "상품명": "product_name"}
    
    payload, has_critical, has_error, has_warning = validate_rows(df, mapping, "COMP_A")
    
    assert has_critical is True

def test_validate_rows_warehouse_optional():
    """warehouse_code 선택 컬럼이 정상적으로 매핑되는지 검증"""
    df = pd.DataFrame([{
        "지점": "서울", "상품명": "마스크", "수량": 100, "날짜": "2026-05-19", "창고": "WH-001"
    }])
    mapping = {
        "지점": "region_code",
        "상품명": "product_name",
        "수량": "quantity",
        "날짜": "date",
        "창고": "warehouse_code"
    }
    payload, has_critical, has_error, has_warning = validate_rows(df, mapping, "COMP_A")
    
    assert payload[0]["standardized_values"]["warehouse_code"] == "WH-001"

def test_validate_rows_nan_product():
    """상품명이 'nan' 문자열일 때 CRITICAL 검증"""
    df, mapping = make_df_and_mapping([
        {"지점": "서울", "상품명": "nan", "수량": 100, "날짜": "2026-05-19"}
    ])
    payload, has_critical, has_error, has_warning = validate_rows(df, mapping, "COMP_A")
    
    assert has_critical is True
