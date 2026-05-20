# tests/test_demand_tracker_extended.py
import pytest
import os
import db
from utils.demand_tracker import calculate_dead_stock_cost, log_stock_out, aggregate_daily_demand

TEST_DEAD_DB_PATH = "data/test_dead_stock.db"

@pytest.fixture(autouse=True)
def setup_dead_stock_db(monkeypatch):
    monkeypatch.setattr("db.DB_PATH", TEST_DEAD_DB_PATH)
    for suffix in ["", "-wal", "-shm"]:
        path = TEST_DEAD_DB_PATH + suffix
        if os.path.exists(path):
            try:
                os.remove(path)
            except PermissionError:
                pass
    
    db.init_db()
    
    conn = db.get_db_connection()
    conn.execute("INSERT OR IGNORE INTO regions (region_name, region_code) VALUES ('Seoul', 'KR-11')")
    conn.commit()
    conn.close()
    
    yield
    
    for suffix in ["", "-wal", "-shm"]:
        path = TEST_DEAD_DB_PATH + suffix
        if os.path.exists(path):
            try:
                os.remove(path)
            except PermissionError:
                pass

def test_calculate_dead_stock_cost_no_dead_stock():
    """DoS <= 90 인 경우 방치 재고 비용 0"""
    cost = calculate_dead_stock_cost("KR-11", "Mask", 100.0, 10.0)
    # DoS = 100 / 10 = 10 (< 90), cost = 0
    assert cost == 0.0

def test_calculate_dead_stock_cost_dead_stock():
    """DoS > 90 인 경우 방치 재고 비용 산출"""
    cost = calculate_dead_stock_cost("KR-11", "Mask", 1000.0, 5.0)
    # DoS = 1000 / 5 = 200 (> 90), should be > 0
    assert cost > 0.0

def test_calculate_dead_stock_cost_zero_avg():
    """평균 출고가 0인 경우 비용 0"""
    cost = calculate_dead_stock_cost("KR-11", "Mask", 100.0, 0.0)
    assert cost == 0.0

def test_calculate_dead_stock_cost_zero_qty():
    """현재 재고가 0인 경우 비용 0"""
    cost = calculate_dead_stock_cost("KR-11", "Mask", 0.0, 10.0)
    assert cost == 0.0

def test_log_stock_out_zero_qty():
    """출고 수량이 0 이하인 경우 False 반환"""
    assert log_stock_out("KR-11", "Mask", 0.0) is False
    assert log_stock_out("KR-11", "Mask", -10.0) is False

def test_aggregate_daily_demand_no_data():
    """출고 기록이 없는 날짜에도 집계 배치가 정상 동작"""
    result = aggregate_daily_demand(target_date_str="2020-01-01")
    assert result is True
