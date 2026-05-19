# tests/test_dashboard_db_functions.py
import os
import sqlite3
import pytest
import sys
from unittest.mock import MagicMock

# ── Streamlit 의존성 모킹 (pytest Import 시 크래시 방지) ──
mock_st = MagicMock()
sys.modules["streamlit"] = mock_st
sys.modules["streamlit_autorefresh"] = MagicMock()

from db import get_db_connection, init_db

# 테스트용 DB 경로 재정의용 패치
TEST_DB_PATH = "data/test_dashboard_db.db"

@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    """
    테스트용 격리 DB 구성 및 app.py의 DB_PATH 패치
    """
    monkeypatch.setattr("db.DB_PATH", TEST_DB_PATH)
    monkeypatch.setattr("dashboard.app.DB_PATH", TEST_DB_PATH)
    
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
    
    # regions 테이블 기본 데이터 초기화(동적 테스트를 위해 삭제)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM regions")
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

def test_get_db_summary_empty_db():
    """
    DB가 완전히 비어있거나 지점이 등록되지 않았을 때 ZeroDivisionError 없이
    graceful하게 0 또는 기본값을 반환하는지 검증 (Empty State 방어)
    """
    from dashboard.app import get_db_summary
    
    summary = get_db_summary()
    
    assert summary["region_count"] == 0
    assert summary["sku_count"] == 0
    assert summary["total_stock"] == 0.0
    assert summary["alert_count"] == 0
    assert summary["weather_alerts"] == 0
    assert len(summary["region_rows"]) == 0
    assert len(summary["weather_alert_details"]) == 0

def test_get_db_summary_with_data():
    """
    실제 데이터가 유입되었을 때 KPI 카드용 집계 쿼리가 정합하게 총 SKU 수, 총 재고량을 집계하는지 검증
    """
    # 1. 지역 등록
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO regions (region_name, region_code, description) VALUES (?, ?, ?)",
                   ("서울특별시", "KR-11", "서울 기지"))
    cursor.execute("INSERT INTO regions (region_name, region_code, description) VALUES (?, ?, ?)",
                   ("부산광역시", "KR-26", "부산 기지"))
    
    # 2. 재고 적재
    cursor.execute("INSERT INTO region_inventory (region_code, product_name, date, quantity) VALUES (?, ?, ?, ?)",
                   ("KR-11", "MCU 반도체", "2026-05-19", 150.0))
    cursor.execute("INSERT INTO region_inventory (region_code, product_name, date, quantity) VALUES (?, ?, ?, ?)",
                   ("KR-11", "마스크", "2026-05-19", 500.0))
    cursor.execute("INSERT INTO region_inventory (region_code, product_name, date, quantity) VALUES (?, ?, ?, ?)",
                   ("KR-26", "손소독제", "2026-05-19", 300.0))
    
    conn.commit()
    conn.close()
    
    from dashboard.app import get_db_summary
    
    summary = get_db_summary()
    
    assert summary["region_count"] == 2
    assert summary["sku_count"] == 3  # MCU 반도체, 마스크, 손소독제
    assert summary["total_stock"] == 950.0  # 150 + 500 + 300
    assert len(summary["region_rows"]) == 2

def test_get_db_summary_weather_alert_trigger():
    """
    기상 캐시에 폭우(10mm 이상) 또는 극단적 기온이 적재되었을 때 '기상 이변 거점' 집계에 반영되는지 검증
    """
    # 1. 지역 및 기상 데이터 적재 (서울: 폭우 상황)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO regions (region_name, region_code, description) VALUES (?, ?, ?)",
                   ("서울특별시", "KR-11", "서울 기지"))
    cursor.execute("INSERT INTO weather_cache (region_code, date, temp, humidity, precipitation, weather_desc) VALUES (?, ?, ?, ?, ?, ?)",
                   ("KR-11", "2026-05-19", 22.0, 85.0, 15.5, "폭우 경보"))
    conn.commit()
    conn.close()
    
    from dashboard.app import get_db_summary
    
    summary = get_db_summary()
    
    assert summary["weather_alerts"] == 1
    assert len(summary["weather_alert_details"]) == 1
    assert summary["weather_alert_details"][0]["region_name"] == "서울특별시"
    assert summary["weather_alert_details"][0]["precipitation"] == 15.5
