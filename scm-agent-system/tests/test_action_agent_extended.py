# tests/test_action_agent_extended.py
import pytest
import os
import json
import numpy as np
from unittest.mock import MagicMock, patch
from datetime import datetime
import db
from agents.action_agent import ActionAgent, ABSOLUTE_MAX_CAPACITY, MAX_ORDER_CEILING_RATIO
from dto.schemas import BatchInventorySignalDTO, RiskCategory

TEST_ACTION_DB_PATH = "data/test_action_agent.db"

@pytest.fixture(autouse=True)
def setup_action_db(monkeypatch):
    monkeypatch.setattr("db.DB_PATH", TEST_ACTION_DB_PATH)
    for suffix in ["", "-wal", "-shm"]:
        path = TEST_ACTION_DB_PATH + suffix
        if os.path.exists(path):
            try:
                os.remove(path)
            except PermissionError:
                pass
                
    db.init_db()
    
    # 1. 지점 inventory 정보 및 master 데이터 시딩
    conn = db.get_db_connection()
    conn.execute("INSERT OR IGNORE INTO regions (region_name, region_code) VALUES ('Seoul', 'KR-11')")
    conn.execute("INSERT OR IGNORE INTO product_financial_master (product_name, unit_price) VALUES ('SemiConducor_A', 10000.0)")
    
    # Cross-docking을 위한 잉여 지점(Busan) 시딩: DoS > 90, 재고 >= 100
    # DoS = 재고 / moving_avg_30d = 200 / 1 = 200 (> 90)
    conn.execute("INSERT OR IGNORE INTO region_inventory (region_code, product_name, date, quantity) VALUES ('Busan', 'SemiConducor_A', '2026-05-20', 200.0)")
    conn.execute("INSERT OR IGNORE INTO daily_demand_stats (region_code, product_name, date, moving_avg_30d, daily_outbound_total) VALUES ('Busan', 'SemiConducor_A', '2026-05-20', 1.0, 1.0)")
    
    conn.commit()
    conn.close()
    
    yield
    
    for suffix in ["", "-wal", "-shm"]:
        path = TEST_ACTION_DB_PATH + suffix
        if os.path.exists(path):
            try:
                os.remove(path)
            except PermissionError:
                pass

def test_validate_guardrail_absolute_max():
    """발주량 물리적 절대 한계(ABSOLUTE_MAX_CAPACITY) 초과 시 차단(BLOCKED) 검증"""
    agent = ActionAgent()
    # ABSOLUTE_MAX_CAPACITY = 5000
    res = agent._validate_guardrail(ABSOLUTE_MAX_CAPACITY + 1.0)
    assert res["status"] == "BLOCKED"
    assert "절대 상한 초과" in res["reason"]

def test_validate_guardrail_relative_max():
    """발주량이 최근 30일 이동평균의 3배(relative ceiling)를 초과 시 차단(BLOCKED) 검증"""
    agent = ActionAgent()
    # 이력을 5건 이상 시딩하여 상대 가드레일 작동 유도
    # 평균 100, relative_ceiling = 300
    agent._order_history_30d.clear()
    for qty in [100.0, 100.0, 100.0, 100.0, 100.0]:
        agent._order_history_30d.append(qty)
        
    res = agent._validate_guardrail(350.0) # 350 > 300 (BLOCKED)
    assert res["status"] == "BLOCKED"
    assert "상대 상한 초과" in res["reason"]

def test_validate_guardrail_approved():
    """상한선 범위 내의 안전한 발주 요청 승인(APPROVED) 검증"""
    agent = ActionAgent()
    agent._order_history_30d.clear()
    for qty in [100.0, 100.0, 100.0, 100.0, 100.0]:
        agent._order_history_30d.append(qty)
        
    res = agent._validate_guardrail(150.0) # 150 <= 300 (APPROVED)
    assert res["status"] == "APPROVED"

def test_execute_single_cross_docking_and_substitution(tmp_path, monkeypatch):
    """
    [Cross-docking & Substitution]
    잉여 재고가 있는 타 지점에서 재고를 끌어와 신규 조달 원가(saved_cost)를 절감하고
    원래 발주 요청량 중 대체 수량을 뺀 만큼만 최종 발주(PO)하는 자율 대체 메커니즘 검증.
    """
    # outputs/order_list.json의 저장 경로를 격리된 임시 공간으로 mock
    order_json_path = tmp_path / "order_list.json"
    monkeypatch.setattr("os.path.exists", lambda path: False)
    
    # Mock the REST API client post
    from agents.api_client import client
    monkeypatch.setattr(client, "post", lambda url, payload: {
        "rebalancedQty": 50.0,
        "transfers": [
            {
                "fromRegion": "BusanHub",
                "transferQty": 50.0,
                "savedCost": 500000
            }
        ]
    })
    
    agent = ActionAgent()
    
    # 부산 지점의 200개 잉여 재고 중 90일치 안전망(1 * 90 = 90개)을 뺀 110개 전송 가능
    # 50개 발주 시, 50개 전체 자율 대체 가능하므로 신규 발주는 0이 되어 취소됨
    res = agent.execute_and_publish(
        item_name="SemiConducor_A",
        quantity=50.0,
        category=RiskCategory.TECH_AND_SEMICONDUCTOR
    )
    
    assert res["status"] == "APPROVED"
    assert "자율 대체 완료" in res["reason"]
    assert res["order_id"].startswith("REBAL-")

def test_execute_batch_numpy_matrix_guardrails():
    """NumPy 고성능 행렬 연산을 활용한 대량 SKU 일중 가드레일 필터링 및 30일 이력 업데이트 행렬 연산 검증"""
    agent = ActionAgent()
    
    # 30,490개 SKU를 모방한 30490개 크기의 NumPy 배열 테스트
    # 가드레일 한계: 절대 상한 5000 (설정 파일 기준)
    optimal_order_qtys = np.zeros(30490)
    optimal_order_qtys[0] = 100.0
    optimal_order_qtys[1] = 6000.0  # 6000 > 5000 (절대 상한 초과 차단 유도)
    optimal_order_qtys[2] = 150.0
    optimal_order_qtys[3] = 0.0
    optimal_order_qtys[4] = 50.0
    
    safety_stocks = np.full(30490, 50.0)
    reorder_points = np.full(30490, 120.0)
    
    alert_levels = np.full(30490, "WARNING", dtype=object)
    alert_levels[1] = "CRITICAL"
    alert_levels[3] = "NORMAL"
    
    # BatchInventorySignalDTO 필드에 맞게 선언 (mode 제외)
    signal = BatchInventorySignalDTO(
        timestamp=datetime.now().isoformat(),
        day=1,
        safety_stocks=safety_stocks,
        reorder_points=reorder_points,
        optimal_order_qtys=optimal_order_qtys,
        confidence_level=0.95,
        alert_levels=alert_levels
    )
    
    # 이력이 아직 5일 미만이므로 절대 상한(5000초과한 6000)만 차단되어야 함
    res = agent.execute_batch(signal)
    
    assert res["approved_count"] == 30489
    assert res["blocked_count"] == 1
    assert res["status"][1] == "BLOCKED"
    assert res["status"][0] == "APPROVED"
    assert res["approved_qty"][1] == 0.0
    assert res["approved_qty"][0] == 100.0
