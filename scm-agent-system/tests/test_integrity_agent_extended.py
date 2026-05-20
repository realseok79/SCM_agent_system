# tests/test_integrity_agent_extended.py
import pytest
import os
import db
from agents.integrity_agent import verify_stock_integrity

TEST_INTEG_DB_PATH = "data/test_integrity.db"

@pytest.fixture(autouse=True)
def setup_integrity_db(monkeypatch):
    monkeypatch.setattr("db.DB_PATH", TEST_INTEG_DB_PATH)
    for suffix in ["", "-wal", "-shm"]:
        path = TEST_INTEG_DB_PATH + suffix
        if os.path.exists(path):
            try:
                os.remove(path)
            except PermissionError:
                pass
    
    db.init_db()
    yield
    
    for suffix in ["", "-wal", "-shm"]:
        path = TEST_INTEG_DB_PATH + suffix
        if os.path.exists(path):
            try:
                os.remove(path)
            except PermissionError:
                pass

def test_verify_stock_integrity_missing_data():
    """어제 또는 오늘 재고 데이터가 부족할 때 무결성 검사 조기 중단(has_discrepancy=False) 검증"""
    res = verify_stock_integrity(region_code="KR-11", product_name="Mask", target_date_str="2026-05-20")
    assert res["has_discrepancy"] is False
    assert "데이터가 부족합니다" in res["message"]

def test_verify_stock_integrity_perfect_match():
    """전산 변동량과 실제 트랜잭션 출고량이 완벽히 일치할 때 데이터 무결성 검증"""
    conn = db.get_db_connection()
    # 어제 재고 100, 오늘 재고 80 (변동량 20)
    conn.execute("INSERT INTO region_inventory (region_code, product_name, date, quantity) VALUES ('KR-11', 'Mask', '2026-05-19', 100.0)")
    conn.execute("INSERT INTO region_inventory (region_code, product_name, date, quantity) VALUES ('KR-11', 'Mask', '2026-05-20', 80.0)")
    # 실제 출고 합계 20
    conn.execute("INSERT INTO daily_demand_stats (region_code, product_name, date, daily_outbound_total) VALUES ('KR-11', 'Mask', '2026-05-20', 20.0)")
    conn.commit()
    conn.close()
    
    res = verify_stock_integrity(region_code="KR-11", product_name="Mask", target_date_str="2026-05-20")
    assert res["has_discrepancy"] is False
    assert "완벽히 일치하여" in res["message"]

def test_verify_stock_integrity_shrinkage_detected():
    """전산 재고가 실제 출고량보다 더 줄어들었을 때 유실(Shrinkage) 감지 및 누수 금액 산출 검증"""
    conn = db.get_db_connection()
    # 어제 재고 100, 오늘 재고 70 (변동량 30)
    conn.execute("INSERT INTO region_inventory (region_code, product_name, date, quantity) VALUES ('KR-11', 'Mask', '2026-05-19', 100.0)")
    conn.execute("INSERT INTO region_inventory (region_code, product_name, date, quantity) VALUES ('KR-11', 'Mask', '2026-05-20', 70.0)")
    # 실제 출고 합계 20 (즉 10개 유실 발생)
    conn.execute("INSERT INTO daily_demand_stats (region_code, product_name, date, daily_outbound_total) VALUES ('KR-11', 'Mask', '2026-05-20', 20.0)")
    # 상품 단가 마스터 등록 (1000원)
    conn.execute("INSERT INTO product_financial_master (product_name, unit_price, holding_cost_per_day) VALUES ('Mask', 1000.0, 0.5)")
    conn.commit()
    conn.close()
    
    res = verify_stock_integrity(region_code="KR-11", product_name="Mask", target_date_str="2026-05-20")
    assert res["has_discrepancy"] is True
    assert res["shrinkage_qty"] == 10.0
    assert res["shrinkage_cost"] == 10000.0  # 10개 * 1000원
    assert "원인 불명 유실" in res["message"]

def test_verify_stock_integrity_excess_outbound():
    """실제 출고량이 전산 재고 변동량보다 클 때 (초과 출고) 경고 검증"""
    conn = db.get_db_connection()
    # 어제 재고 100, today 재고 90 (변동량 10)
    conn.execute("INSERT INTO region_inventory (region_code, product_name, date, quantity) VALUES ('KR-11', 'Mask', '2026-05-19', 100.0)")
    conn.execute("INSERT INTO region_inventory (region_code, product_name, date, quantity) VALUES ('KR-11', 'Mask', '2026-05-20', 90.0)")
    # 실제 출고 합계 25 (출고가 변동량을 초과함)
    conn.execute("INSERT INTO daily_demand_stats (region_code, product_name, date, daily_outbound_total) VALUES ('KR-11', 'Mask', '2026-05-20', 25.0)")
    conn.commit()
    conn.close()
    
    res = verify_stock_integrity(region_code="KR-11", product_name="Mask", target_date_str="2026-05-20")
    assert res["has_discrepancy"] is True
    assert res["shrinkage_qty"] == -15.0  # 초과 출고
    assert "초과 출고" in res["message"]

def test_verify_stock_integrity_default_today():
    """target_date_str을 지정하지 않았을 때 안전하게 오늘 날짜로 동작하는지 검증"""
    res = verify_stock_integrity(region_code="KR-11", product_name="Mask", target_date_str=None)
    assert "yesterday_qty" in res
