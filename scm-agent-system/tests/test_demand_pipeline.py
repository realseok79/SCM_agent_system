# tests/test_demand_pipeline.py
import os
import sys
import datetime
import pytest
from unittest.mock import MagicMock

# ── Streamlit 의존성 모킹 ──
mock_st = MagicMock()
def mock_decorator(*args, **kwargs):
    def decorator(func):
        return func
    return decorator
mock_st.cache_data = mock_decorator
mock_st.cache_resource = mock_decorator
sys.modules["streamlit"] = mock_st
sys.modules["streamlit_autorefresh"] = MagicMock()

TEST_DB_PATH = "data/test_demand.db"
os.environ["DB_PATH"] = TEST_DB_PATH

import db
db.DB_PATH = TEST_DB_PATH

from db import init_db, get_db_connection
from utils.demand_tracker import log_stock_out, aggregate_daily_demand
from agents.integrity_agent import verify_stock_integrity

@pytest.fixture(autouse=True)
def setup_test_db():
    """
    각 테스트 실행 전 임시 DB 초기화 및 기본 지점 정보/재고 데이터 세팅
    """
    init_db()
    
    # 테이블 내 기존 레코드 클린업 (동일 커넥션 내 청소)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM stock_out_logs")
        cursor.execute("DELETE FROM daily_demand_stats")
        cursor.execute("DELETE FROM region_inventory")
        cursor.execute("DELETE FROM regions")
        conn.commit()
    except Exception:
        pass
    
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    yesterday_str = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    
    # 1. 지점 등록
    cursor.execute("INSERT OR IGNORE INTO regions (region_name, region_code) VALUES (?, ?)", ("서울특별시", "KR-11"))
    
    # 2. 전산 재고량 등록 (어제 5000개 -> 오늘 4900개: 전산상 100개 감소)
    cursor.execute("""
        INSERT OR IGNORE INTO region_inventory (region_code, product_name, date, quantity)
        VALUES (?, ?, ?, ?)
    """, ("KR-11", "종합 품목", yesterday_str, 5000.0))
    
    cursor.execute("""
        INSERT OR IGNORE INTO region_inventory (region_code, product_name, date, quantity)
        VALUES (?, ?, ?, ?)
    """, ("KR-11", "종합 품목", today_str, 4900.0))
    
    conn.commit()
    conn.close()
    
    yield
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM stock_out_logs")
        cursor.execute("DELETE FROM daily_demand_stats")
        cursor.execute("DELETE FROM region_inventory")
        cursor.execute("DELETE FROM regions")
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()

def test_log_stock_out_success():
    """
    정상적인 출고 기록이 stock_out_logs에 적재되는지 검증
    """
    assert log_stock_out(region_code="KR-11", product_name="종합 품목", outbound_qty=20.0, transaction_type="정상출고") is True
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT region_code, product_name, outbound_qty, transaction_type FROM stock_out_logs")
    row = cursor.fetchone()
    conn.close()
    
    assert row is not None
    assert row["region_code"] == "KR-11"
    assert row["product_name"] == "종합 품목"
    assert row["outbound_qty"] == 20.0
    assert row["transaction_type"] == "정상출고"

def test_aggregate_daily_demand_and_moving_avg():
    """
    일일 트랜잭션 집계 및 30일 이동평균 수치가 정확하게 계산/저장되는지 검증
    """
    # 2회 트랜잭션 적재 (합계: 80개)
    log_stock_out("KR-11", "종합 품목", 30.0)
    log_stock_out("KR-11", "종합 품목", 50.0)
    
    # 집계 배치 가동
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    assert aggregate_daily_demand(target_date_str=today_str) is True
    
    # 검증
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT daily_outbound_total, moving_avg_30d FROM daily_demand_stats WHERE region_code='KR-11' AND date=?", (today_str,))
    row = cursor.fetchone()
    conn.close()
    
    assert row is not None
    assert row["daily_outbound_total"] == 80.0
    # 30일 간 첫 기록이므로 평균도 80.0
    assert row["moving_avg_30d"] == 80.0

def test_verify_stock_integrity_discrepancy():
    """
    전산상 재고 변동량(100개 감소)과 실제 출고 트랜잭션 합계(80개) 간의 
    무결성 불일치(Shrinkage 20개 발생)가 정확히 감지되는지 검증
    """
    # 1. 실제 출고로그 80개 적재 후 일별 집계
    log_stock_out("KR-11", "종합 품목", 80.0)
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    aggregate_daily_demand(target_date_str=today_str)
    
    # 2. 무결성 검증
    result = verify_stock_integrity("KR-11", "종합 품목", today_str)
    
    # 3. 단언 (Assertion)
    assert result["has_discrepancy"] is True
    assert result["computed_delta"] == 100.0  # 전산상 5000 -> 4900 (100개 감소)
    assert result["actual_outbound"] == 80.0  # 실제 출고 80개
    assert "20.0개" in result["message"]
    assert "원인 불명 유실(Shrinkage)" in result["message"]

def test_verify_stock_integrity_matching():
    """
    전산상 재고 변동량(100개 감소)과 실제 출고 트랜잭션 합계(100개)가 
    완벽히 일치하여 무결성 통과가 이루어지는지 검증
    """
    # 1. 실제 출고로그 100개 적재 후 일별 집계
    log_stock_out("KR-11", "종합 품목", 100.0)
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    aggregate_daily_demand(target_date_str=today_str)
    
    # 2. 무결성 검증
    result = verify_stock_integrity("KR-11", "종합 품목", today_str)
    
    # 3. 단언 (Assertion)
    assert result["has_discrepancy"] is False
    assert result["shrinkage_qty"] == 0.0
    assert "완벽히 일치하여 데이터 무결성이 검증되었습니다." in result["message"]
