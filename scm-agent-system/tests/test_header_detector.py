# tests/test_header_detector.py
import pytest
import pandas as pd
from utils.parser.header_detector import detect_header_row, extract_clean_df, clean_value

def test_clean_value_basic():
    """기본 문자열 정형화 검증"""
    assert clean_value("  서울  ") == "서울"
    assert clean_value("Product_Name") == "productname"
    assert clean_value("Region-Code") == "regioncode"
    assert clean_value(None) == ""
    assert clean_value(float('nan')) == ""

def test_detect_header_row_columns_already_correct():
    """DataFrame의 기존 컬럼이 이미 올바른 헤더인 경우 -1 반환"""
    df = pd.DataFrame({
        "지점": ["서울", "부산"],
        "상품명": ["마스크", "손소독제"],
        "수량": [100, 200],
        "날짜": ["2026-05-19", "2026-05-20"]
    })
    result = detect_header_row(df)
    assert result == -1

def test_detect_header_row_hidden_in_data():
    """실제 헤더가 데이터 행 내부에 숨겨진 경우 올바른 인덱스 반환"""
    df = pd.DataFrame({
        0: ["기업 보고서", "지점", "서울", "부산"],
        1: ["2026년 5월", "상품명", "마스크", "손소독제"],
        2: ["V1.0", "수량", "100", "200"],
        3: ["작성자", "날짜", "2026-05-19", "2026-05-20"]
    })
    result = detect_header_row(df)
    assert result == 1  # 두 번째 행(index 1)에 헤더 존재

def test_detect_header_row_english_aliases():
    """영문 별칭 헤더 인식 검증"""
    df = pd.DataFrame({
        0: ["metadata row", "region", "Seoul", "Busan"],
        1: ["ignore", "product", "Mask", "Sanitizer"],
        2: ["ignore", "qty", "100", "200"],
        3: ["ignore", "date", "2026-05-19", "2026-05-20"]
    })
    result = detect_header_row(df)
    assert result == 1

def test_extract_clean_df_header_minus_one():
    """header_idx가 -1이면 원본 DataFrame을 그대로 복사 반환"""
    df = pd.DataFrame({"지점": ["서울"], "수량": [100]})
    result = extract_clean_df(df, -1)
    assert list(result.columns) == ["지점", "수량"]
    assert len(result) == 1

def test_extract_clean_df_slicing():
    """헤더 행으로부터 DataFrame을 올바르게 슬라이싱"""
    df = pd.DataFrame({
        0: ["노이즈", "지점", "서울", "부산"],
        1: ["노이즈", "상품명", "마스크", "손소독제"],
        2: ["노이즈", "수량", "100", "200"]
    })
    result = extract_clean_df(df, 1)
    assert list(result.columns) == ["지점", "상품명", "수량"]
    assert len(result) == 2
    assert result.iloc[0].iloc[0] == "서울"

def test_extract_clean_df_unnamed_columns():
    """NaN 컬럼이 UNNAMED_COL_N 플레이스홀더로 대체되는지 검증"""
    df = pd.DataFrame({
        0: ["지점", "서울"],
        1: [None, "마스크"],
        2: ["수량", "100"]
    })
    result = extract_clean_df(df, 0)
    assert "UNNAMED_COL_1" in result.columns

def test_detect_header_row_no_match():
    """어떤 행에서도 매칭이 안 되는 경우"""
    df = pd.DataFrame({
        0: ["xyz", "abc"],
        1: ["123", "456"]
    })
    result = detect_header_row(df)
    # 매칭이 0이면 col_matches >= max_matches (0 >= 0) 이므로 -1 또는 0
    assert result in [-1, 0]
