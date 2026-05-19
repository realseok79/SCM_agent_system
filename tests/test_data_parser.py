# tests/test_data_parser.py
import os
import sqlite3
import pytest
import pandas as pd
from datetime import datetime

from db import get_db_connection, init_db
from models import standardize_region

# 테스트용 DB 경로 재정의용 패치
TEST_DB_PATH = "data/test_sigma_enterprise.db"

@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    """
    테스트 실행 전 테스트용 DB를 초기화하고 임시로 DB_PATH를 변경합니다.
    """
    # db.py의 DB_PATH를 임시로 테스트용 파일로 패치
    monkeypatch.setattr("db.DB_PATH", TEST_DB_PATH)
    
    # 만약 기존 테스트 DB 파일이 있다면 삭제
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
            # WAL 관련 임시 파일들도 정리
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
        "INSERT INTO regions (region_name, region_code, description) VALUES (?, ?, ?)",
        ("서울특별시", "KR-11", "서울 메인 허브")
    )
    cursor.execute(
        "INSERT INTO regions (region_name, region_code, description) VALUES (?, ?, ?)",
        ("부산광역시", "KR-26", "부산 메인 허브")
    )
    conn.commit()
    conn.close()
    
    yield
    
    # 테스트 종료 후 파일 삭제
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
            if os.path.exists(TEST_DB_PATH + "-wal"):
                os.remove(TEST_DB_PATH + "-wal")
            if os.path.exists(TEST_DB_PATH + "-shm"):
                os.remove(TEST_DB_PATH + "-shm")
        except PermissionError:
            pass

def test_parse_and_route_success(tmp_path, monkeypatch):
    """
    정상적인 CSV 파일 업로드 시 데이터가 올바른 표준 지역 테이블로 라우팅되는지 확인
    """
    from utils.data_parser import parse_and_route_file
    monkeypatch.setattr("utils.data_parser.DB_PATH", TEST_DB_PATH)
    
    csv_file = tmp_path / "normal_data.csv"
    df = pd.DataFrame({
        "지점": ["서울", "부산", "서울특별시"],
        "상품명": ["마스크", "손소독제", "MCU 반도체"],
        "수량": [100.0, 250.0, 500.0],
        "날짜": ["2026-05-19", "2026-05-19", "2026-05-20"]
    })
    df.to_csv(csv_file, index=False, encoding="utf-8")
    
    # 파싱 및 라우팅 수행
    stats = parse_and_route_file(str(csv_file))
    
    assert stats["success_count"] == 3
    assert stats["error_count"] == 0
    
    # DB 결과 검증
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT region_code, product_name, date, quantity FROM region_inventory ORDER BY region_code, product_name")
    rows = cursor.fetchall()
    conn.close()
    
    assert len(rows) == 3
    # 서울: 서울 -> 서울특별시 -> KR-11
    assert rows[0]["region_code"] == "KR-11"
    assert rows[0]["product_name"] == "MCU 반도체"
    assert rows[0]["quantity"] == 500.0
    
    assert rows[1]["region_code"] == "KR-11"
    assert rows[1]["product_name"] == "마스크"
    assert rows[1]["quantity"] == 100.0
    
    # 부산: 부산 -> 부산광역시 -> KR-26
    assert rows[2]["region_code"] == "KR-26"
    assert rows[2]["product_name"] == "손소독제"
    assert rows[2]["quantity"] == 250.0

def test_parse_and_route_shuffled_columns(tmp_path, monkeypatch):
    """
    열 순서가 섞이고 다양한 한글/영어 별칭 컬럼명이 사용되어도 퍼지 매칭으로 정상 인식하는지 확인
    """
    from utils.data_parser import parse_and_route_file
    monkeypatch.setattr("utils.data_parser.DB_PATH", TEST_DB_PATH)
    
    csv_file = tmp_path / "shuffled_data.csv"
    # 수량, 날짜, 지역명, 품목으로 순서 섞기 및 비정형 헤더 사용
    df = pd.DataFrame({
        "QTY": [120, 80],
        "일자": ["2026-05-18", "2026-05-18"],
        "RegionName": ["seoul", "부산"],
        "product_title": ["마스크", "손소독제"]
    })
    df.to_csv(csv_file, index=False, encoding="utf-8")
    
    stats = parse_and_route_file(str(csv_file))
    
    assert stats["success_count"] == 2
    assert stats["error_count"] == 0
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT region_code, product_name, quantity, date FROM region_inventory WHERE date = '2026-05-18'")
    rows = cursor.fetchall()
    conn.close()
    
    assert len(rows) == 2
    mapped_dict = {row["region_code"]: row for row in rows}
    assert "KR-11" in mapped_dict
    assert mapped_dict["KR-11"]["product_name"] == "마스크"
    assert mapped_dict["KR-11"]["quantity"] == 120.0
    
    assert "KR-26" in mapped_dict
    assert mapped_dict["KR-26"]["product_name"] == "손소독제"
    assert mapped_dict["KR-26"]["quantity"] == 80.0

def test_parse_and_route_missing_date_fallback(tmp_path, monkeypatch):
    """
    날짜 컬럼이 완전히 누락된 경우, 업로드 당일 날짜(오늘 YYYY-MM-DD)로 자동 대체 적재되는지 검증
    """
    from utils.data_parser import parse_and_route_file
    monkeypatch.setattr("utils.data_parser.DB_PATH", TEST_DB_PATH)
    
    csv_file = tmp_path / "missing_date.csv"
    df = pd.DataFrame({
        "지점": ["서울"],
        "상품명": ["마스크"],
        "수량": [999.0]
    })
    df.to_csv(csv_file, index=False, encoding="utf-8")
    
    stats = parse_and_route_file(str(csv_file))
    
    assert stats["success_count"] == 1
    assert stats["error_count"] == 0
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT region_code, product_name, date, quantity FROM region_inventory")
    row = cursor.fetchone()
    conn.close()
    
    assert row is not None
    assert row["region_code"] == "KR-11"
    assert row["product_name"] == "마스크"
    assert row["quantity"] == 999.0
    # 오늘 날짜 형식(YYYY-MM-DD) 검증
    today_str = datetime.now().strftime("%Y-%m-%d")
    assert row["date"] == today_str

def test_parse_and_route_upsert_behavior(tmp_path, monkeypatch):
    """
    동일한 '지역 + 상품 + 날짜' 조합 업로드 시 데이터가 누적(Add)되거나 복제(Duplicate)되지 않고,
    기존 레코드의 수량이 정상적으로 업데이트(UPSERT) 되는지 검증
    """
    from utils.data_parser import parse_and_route_file
    monkeypatch.setattr("utils.data_parser.DB_PATH", TEST_DB_PATH)
    
    # 1차 업로드
    csv_file_1 = tmp_path / "upsert_1.csv"
    df1 = pd.DataFrame({
        "지점": ["서울"],
        "상품명": ["마스크"],
        "수량": [100.0],
        "날짜": ["2026-05-19"]
    })
    df1.to_csv(csv_file_1, index=False, encoding="utf-8")
    parse_and_route_file(str(csv_file_1))
    
    # 2차 업로드 (수량 수정)
    csv_file_2 = tmp_path / "upsert_2.csv"
    df2 = pd.DataFrame({
        "지점": ["서울"],
        "상품명": ["마스크"],
        "수량": [175.0],  # 100 -> 175로 변경
        "날짜": ["2026-05-19"]
    })
    df2.to_csv(csv_file_2, index=False, encoding="utf-8")
    parse_and_route_file(str(csv_file_2))
    
    # 검증
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT region_code, product_name, date, quantity FROM region_inventory")
    rows = cursor.fetchall()
    conn.close()
    
    assert len(rows) == 1  # 레코드는 여전히 1개여야 함 (복제 방지)
    assert rows[0]["quantity"] == 175.0  # 175로 업데이트 되었어야 함 (UPSERT 작동 완료)

def test_parse_and_route_invalid_region(tmp_path, monkeypatch):
    """
    지원하지 않는 잘못된 지역명이 포함된 행 업로드 시, 예외 처리되어 실패 수량에 반영되고
    DB에 해당 데이터가 적재되지 않는지 검증
    """
    from utils.data_parser import parse_and_route_file
    monkeypatch.setattr("utils.data_parser.DB_PATH", TEST_DB_PATH)
    
    csv_file = tmp_path / "invalid_region.csv"
    df = pd.DataFrame({
        "지점": ["안드로메다"],
        "상품명": ["마스크"],
        "수량": [100.0],
        "날짜": ["2026-05-19"]
    })
    df.to_csv(csv_file, index=False, encoding="utf-8")
    
    stats = parse_and_route_file(str(csv_file))
    
    assert stats["success_count"] == 0
    assert stats["error_count"] == 1
    assert "안드로메다" in stats["errors"][0]
    
    # DB 검증: 레코드가 비어있어야 함
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM region_inventory")
    count = cursor.fetchone()[0]
    conn.close()
    
    assert count == 0
