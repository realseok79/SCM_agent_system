# tests/test_data_parser_extended.py
import pytest
import os
import sqlite3
import pandas as pd
import db
from utils.data_parser import parse_and_route_file

TEST_PARSER_DB_PATH = "data/test_data_parser.db"

@pytest.fixture(autouse=True)
def setup_parser_db(monkeypatch):
    monkeypatch.setattr("db.DB_PATH", TEST_PARSER_DB_PATH)
    for suffix in ["", "-wal", "-shm"]:
        path = TEST_PARSER_DB_PATH + suffix
        if os.path.exists(path):
            try:
                os.remove(path)
            except PermissionError:
                pass
                
    db.init_db()
    # regions에 사전 마스터 데이터 등록
    conn = db.get_db_connection()
    conn.execute("INSERT OR IGNORE INTO regions (region_name, region_code) VALUES ('Seoul', 'KR-11')")
    conn.commit()
    conn.close()
    
    yield
    
    for suffix in ["", "-wal", "-shm"]:
        path = TEST_PARSER_DB_PATH + suffix
        if os.path.exists(path):
            try:
                os.remove(path)
            except PermissionError:
                pass

def test_parse_and_route_file_not_found():
    """존재하지 않는 파일 경로 유입 시 FileNotFoundError 발생 검증"""
    with pytest.raises(FileNotFoundError):
        parse_and_route_file("data/nonexistent_file_123.csv")

def test_parse_and_route_unsupported_format(tmp_path):
    """비지원 확장자(txt) 파일 유입 시 ValueError 발생 검증"""
    bad_file = tmp_path / "data.txt"
    bad_file.write_text("region,product,quantity\nKR-11,Part_A,100")
    
    with pytest.raises(ValueError) as exc_info:
        parse_and_route_file(str(bad_file))
    assert "지원하지 않는 파일 형식" in str(exc_info.value)

def test_parse_and_route_missing_required_headers(tmp_path):
    """필수 헤더(수량 등) 누락 시 ValueError 검증"""
    bad_file = tmp_path / "missing_qty.csv"
    # quantity가 누락된 데이터
    df = pd.DataFrame([{"region": "Seoul", "product": "Part_A"}])
    df.to_csv(bad_file, index=False)
    
    with pytest.raises(ValueError) as exc_info:
        parse_and_route_file(str(bad_file))
    assert "필수 컬럼이 누락되었습니다" in str(exc_info.value)

def test_parse_and_route_invalid_row_handling(tmp_path):
    """일부 행에 상품명 누락(NaN) 또는 음수 수량이 있을 때 정상 스킵 및 에러 리스트 수집 검증"""
    csv_file = tmp_path / "invalid_rows.csv"
    df = pd.DataFrame([
        {"region": "Seoul", "product": "Part_A", "quantity": 100.0, "date": "2026-05-20"}, # 정상
        {"region": "Seoul", "product": "", "quantity": 50.0, "date": "2026-05-20"},       # 상품명 빈값 (에러)
        {"region": "Seoul", "product": "Part_B", "quantity": -10.0, "date": "2026-05-20"},   # 수량 음수 (에러)
        {"region": "Seoul", "product": "Part_C", "quantity": None, "date": "2026-05-20"}    # 수량 NaN (에러)
    ])
    df.to_csv(csv_file, index=False)
    
    res = parse_and_route_file(str(csv_file))
    assert res["success_count"] == 1
    assert res["error_count"] == 3
    assert len(res["errors"]) >= 3
    assert "상품명이 비어있습니다" in res["errors"][0]
    assert "음수일 수 없습니다" in res["errors"][1]
    assert "누락되었습니다" in res["errors"][2]

def test_parse_and_route_invalid_date_recovery(tmp_path):
    """날짜 형식이 비어있거나 훼손되었을 때 오늘 날짜 기본값으로 자동 복구 검증"""
    csv_file = tmp_path / "invalid_date.csv"
    df = pd.DataFrame([
        {"region": "Seoul", "product": "Part_A", "quantity": 100.0, "date": ""}  # 날짜 빈칸
    ])
    df.to_csv(csv_file, index=False)
    
    res = parse_and_route_file(str(csv_file))
    assert res["success_count"] == 1
    
    # DB에 적재된 오늘 날짜 데이터 확인
    conn = db.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT date FROM region_inventory WHERE product_name = 'Part_A'")
    row = cursor.fetchone()
    assert row is not None
    assert len(row["date"]) == 10  # YYYY-MM-DD 형식
    conn.close()
