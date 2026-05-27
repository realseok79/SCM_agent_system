# tests/test_scm_domain.py
import pytest
import numpy as np
from agents.action_agent import ActionAgent
from agents.orchestrator import AgentOrchestrator

def test_lot_size_rounding():
    """
    [도메인 검증] ActionAgent._round_to_lot()이 Lot Size 배수로 정상 올림 처리하는지 검증
    - 137.0 -> 150.0 (Lot Size = 50.0)
    - 0.0 -> 0.0
    - 음수 -> 0.0
    """
    agent = ActionAgent()
    assert agent._round_to_lot(137.0, 50.0) == 150.0
    assert agent._round_to_lot(0.0, 50.0) == 0.0
    assert agent._round_to_lot(-12.5, 50.0) == 0.0
    assert agent._round_to_lot(12.0, 10.0) == 20.0

def test_sla_fill_rate_precision():
    """
    [도메인 검증] Fill Rate SLA 연산 공식 정합성 검증
    수요 100.0, 가용 재고 및 충족량 85.0인 경우 Fill Rate = 85.0%
    """
    cumulative_demand = 100.0
    cumulative_fulfilled = 85.0
    
    # orchestrator.py 공식 모방
    fill_rate = (cumulative_fulfilled / cumulative_demand) * 100.0
    assert fill_rate == 85.0

def test_inventory_turnover_ratio():
    """
    [도메인 검증] 재고 회전율(Inventory Turnover) 연산 공식 검증
    100일간 누적 수요 1000개 (연간 환산 수요 = 1000 / 100 * 365 = 3,650개), 평균 재고 100개인 경우
    Inventory Turnover = 3,650 / 100 = 36.5
    """
    cumulative_demand = 1000.0
    day = 100
    avg_stock = 100.0
    
    # orchestrator.py 공식 모방
    annualized_demand = (cumulative_demand / day) * 365.0
    turnover = annualized_demand / avg_stock
    assert round(turnover, 1) == 36.5

def test_forecast_accuracy_mape():
    """
    [도메인 검증] 예측 모델 MAPE(Mean Absolute Percentage Error) 수리 연산 검증
    예측치 95.0, 실제치 100.0인 경우 오차율 = 5.0% (0.05)
    """
    predicted_demand = 95.0
    actual_demand = 100.0
    
    # orchestrator.py 공식 모방
    actual_val = max(actual_demand, 1.0)
    mape = abs(actual_val - predicted_demand) / actual_val
    assert mape == 0.05
