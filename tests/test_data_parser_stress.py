# tests/test_data_parser_stress.py
import os
import sqlite3
import pytest
import pandas as pd
from datetime import datetime

from db import get_db_connection, init_db

# 테스트용 DB 경로 재정의용 패치
TEST_DB_PATH = "data/test_sigma_enterprise_stress.db"

@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    """
    테스트 실행 전 테스트용 DB를 초기화하고 임시로 DB_PATH를 변경합니다.
    """
    monkeypatch.setattr("db.DB_PATH", TEST_DB_PATH)
    monkeypatch.setattr("utils.data_parser.DB_PATH", TEST_DB_PATH)
    
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
            if os.path.exists(TEST_DB_PATH + "-wal"):
                os.remove(TEST_DB_PATH + "-wal")
            if os.path.exists(TEST_DB_PATH + "-shm"):
                os.remove(TEST_DB_PATH + "-shm")
        except PermissionError:
            pass
            
    init_db()
    
    # 테스트용 기본 지역(Region) 데이터 삽입
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO regions (region_name, region_code, description) VALUES (?, ?, ?)",
        ("서울특별시", "KR-11", "서울 메인 허브")
    )
    cursor.execute(
        "INSERT OR IGNORE INTO regions (region_name, region_code, description) VALUES (?, ?, ?)",
        ("부산광역시", "KR-26", "부산 메인 허브")
    )
    conn.commit()
    conn.close()
    
    yield
    
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
            if os.path.exists(TEST_DB_PATH + "-wal"):
                os.remove(TEST_DB_PATH + "-wal")
            if os.path.exists(TEST_DB_PATH + "-shm"):
                os.remove(TEST_DB_PATH + "-shm")
        except PermissionError:
            pass

def test_bulk_upload_1000_rows(tmp_path):
    """
    실제 SKU 1,000개 분량의 재고 데이터 업로드 시 DB에 고속으로 정상 UPSERT되는지 검증
    """
    from utils.data_parser import parse_and_route_file
    
    csv_file = tmp_path / "bulk_1000.csv"
    
    # 1,000행 데이터 생성 (서울과 부산 교대)
    regions = ["서울", "부산"]
    products = [f"Item-{i}" for i in range(1000)]
    quantities = [100.0 + i for i in range(1000)]
    dates = [datetime.now().strftime("%Y-%m-%d")] * 1000
    
    df = pd.DataFrame({
        "지점": [regions[i % 2] for i in range(1000)],
        "상품명": products,
        "수량": quantities,
        "날짜": dates
    })
    df.to_csv(csv_file, index=False, encoding="utf-8")
    
    stats = parse_and_route_file(str(csv_file))
    
    assert stats["success_count"] == 1000
    assert stats["error_count"] == 0
    assert len(stats["errors"]) == 0
    
    # DB SUM 검증
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(quantity) FROM region_inventory")
    total_qty = cursor.fetchone()[0]
    conn.close()
    
    expected_sum = sum(quantities)
    assert total_qty == pytest.approx(expected_sum, abs=1e-3)

def test_missing_required_columns(tmp_path):
    """
    필수 컬럼이 누락된 파일 업로드 시 ValueError 발생 및 UI 크래시 방지 검증
    """
    from utils.data_parser import parse_and_route_file
    
    # 1. 지점(region) 컬럼 누락
    csv_file_no_region = tmp_path / "no_region.csv"
    df1 = pd.DataFrame({
        "상품명": ["마스크"],
        "수량": [100.0]
    })
    df1.to_csv(csv_file_no_region, index=False)
    with pytest.raises(ValueError) as exc:
        parse_and_route_file(str(csv_file_no_region))
    assert "필수 컬럼이 누락되었습니다" in str(exc.value)
    
    # 2. 수량(quantity) 컬럼 누락
    csv_file_no_qty = tmp_path / "no_qty.csv"
    df2 = pd.DataFrame({
        "지점": ["서울"],
        "상품명": ["마스크"]
    })
    df2.to_csv(csv_file_no_qty, index=False)
    with pytest.raises(ValueError) as exc:
        parse_and_route_file(str(csv_file_no_qty))
    assert "필수 컬럼이 누락되었습니다" in str(exc.value)

def test_mixed_valid_invalid_rows(tmp_path):
    """
    유효 데이터와 결측치/음수/잘못된 지역 등 무효 데이터가 혼재된 스트레스 상황 검증
    """
    from utils.data_parser import parse_and_route_file
    
    csv_file = tmp_path / "mixed.csv"
    df = pd.DataFrame({
        "지점": ["서울", "안드로메다", "부산", "서울", "부산"],
        "상품명": ["마스크", "손소독제", "MCU 반도체", "마스크", "손소독제"],
        "수량": [100.0, 50.0, -10.0, None, 200.0],
        "날짜": ["2026-05-19"] * 5
    })
    df.to_csv(csv_file, index=False, encoding="utf-8")
    
    stats = parse_and_route_file(str(csv_file))
    
    # 성공: 2개 (서울 마스크 100, 부산 손소독제 200)
    # 실패: 3개 (잘못된 지역 '안드로메다', 음수 수량 '-10.0', 수량 누락 'None')
    assert stats["success_count"] == 2
    assert stats["error_count"] == 3
    assert len(stats["errors"]) == 3
    
    # 에러 사유 내용 검증
    assert "안드로메다" in stats["errors"][0]
    assert "음수일 수 없습니다" in stats["errors"][1]
    assert "누락되었습니다" in stats["errors"][2]

def test_fuzzy_column_names_extended(tmp_path):
    """
    COLUMN_ALIASES에 있는 다양한 한국어/영어 별칭 매칭 검증
    """
    from utils.data_parser import parse_and_route_file
    
    csv_file = tmp_path / "fuzzy_aliases.csv"
    df = pd.DataFrame({
        "지역명": ["서울"],
        "품목명": ["마스크"],
        "개수": [350.0],
        "기준일": ["2026-05-19"]
    })
    df.to_csv(csv_file, index=False, encoding="utf-8")
    
    stats = parse_and_route_file(str(csv_file))
    assert stats["success_count"] == 1
    assert stats["error_count"] == 0
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT quantity FROM region_inventory")
    qty = cursor.fetchone()[0]
    conn.close()
    assert qty == 350.0

def test_duplicate_upsert_1000_rows(tmp_path):
    """
    대량 1,000행 연속 2회 적재 시 데이터 복제 없이 정확히 UPSERT로 덮어쓰기되는지 검증
    """
    from utils.data_parser import parse_and_route_file
    
    csv_file = tmp_path / "upsert_stress.csv"
    
    # 1. 1차 업로드
    df1 = pd.DataFrame({
        "지점": ["서울"] * 1000,
        "상품명": [f"Item-{i}" for i in range(1000)],
        "수량": [10.0] * 1000,
        "날짜": ["2026-05-19"] * 1000
    })
    df1.to_csv(csv_file, index=False, encoding="utf-8")
    parse_and_route_file(str(csv_file))
    
    # 2. 2차 업로드 (수량 업데이트)
    df2 = pd.DataFrame({
        "지점": ["서울"] * 1000,
        "상품명": [f"Item-{i}" for i in range(1000)],
        "수량": [25.0] * 1000,
        "날짜": ["2026-05-19"] * 1000
    })
    df2.to_csv(csv_file, index=False, encoding="utf-8")
    parse_and_route_file(str(csv_file))
    
    # DB 레코드 수 및 수량 검증
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*), SUM(quantity) FROM region_inventory")
    row = cursor.fetchone()
    conn.close()
    
    assert row[0] == 1000  # 레코드는 복제되지 않고 정확히 1,000개여야 함
    assert row[1] == 25000.0  # 수량은 25.0 * 1000 = 25000.0으로 업데이트되어야 함

def test_error_logging_et_cetera_limit(tmp_path):
    """
    에러가 다수(예: 30개) 발생할 경우, 상위 10개만 상세 노출하고
    나머지는 '외 X개의 에러가 더 발생했습니다. (Et Cetera)'로 요약 노출되는지 검증
    """
    from utils.data_parser import parse_and_route_file
    
    csv_file = tmp_path / "many_errors.csv"
    
    # 30개의 에러 행 생성 (잘못된 지역명 사용)
    df = pd.DataFrame({
        "지점": [f"Invalid-{i}" for i in range(30)],
        "상품명": ["마스크"] * 30,
        "수량": [100.0] * 30,
        "날짜": ["2026-05-19"] * 30
    })
    df.to_csv(csv_file, index=False, encoding="utf-8")
    
    stats = parse_and_route_file(str(csv_file))
    
    assert stats["success_count"] == 0
    assert stats["error_count"] == 30
    
    # 표시된 에러 리스트는 최대 11개여야 함 (상위 10개 + et cetera 요약 1개)
    assert len(stats["errors"]) == 11
    assert "Invalid-0" in stats["errors"][0]
    assert "Invalid-9" in stats["errors"][9]
    assert "외 20개의 에러가 더 발생했습니다. (Et Cetera)" in stats["errors"][10]
