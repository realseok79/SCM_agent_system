# tests/test_decision_agent_unit.py
import pytest
from agents.decision_agent import DecisionAgent

def test_calculate_q_final_logic():
    agent = DecisionAgent()
    
    # Target inventory = d90 (100) + safety_stock (20) = 120
    # Net demand = 120 - current_inv (80) = 40
    # Lot size = 10, MOQ = 50
    # Rounding up: 40 is a multiple of 10 -> 40. MOQ is 50 -> 50.
    q = agent.calculate_q_final(current_inv=80, d90=100, safety_stock=20, moq=50, lot_size=10)
    assert q == 50

    # Target inventory = 120
    # Net demand = 120 - current_inv (115) = 5
    # Rounding up to nearest lot_size (10): 10. MOQ = 5 -> 10.
    q = agent.calculate_q_final(current_inv=115, d90=100, safety_stock=20, moq=5, lot_size=10)
    assert q == 10

    # Target inventory = 120
    # Net demand = 120 - current_inv (150) = -30 (no order needed)
    q = agent.calculate_q_final(current_inv=150, d90=100, safety_stock=20, moq=50, lot_size=10)
    assert q == 0

def test_evaluate_risk_fallback():
    agent = DecisionAgent()
    
    # Since GEMINI_API_KEY might not be set during test execution, it should fallback to heuristics
    context = {
        "current_inventory": 50,
        "d90": 100,
        "safety_stock": 20,
        "moq": 10,
        "lot_size": 5,
        "unit_price": 1000,
        "budget_limit": 5000000,
        "d10": 20,
        "drift_score": 0.5
    }
    
    # Recommended Q: target = 120, net = 70. Rounded to lot_size (5) -> 70.
    res = agent.evaluate_risk("ITEM_001", context)
    assert res["item_id"] == "ITEM_001"
    assert res["recommended_qty"] == 70
    assert res["status"] == "PENDING"  # Fallback forces pending to prevent unchecked auto-approves on network offline
    assert "Fallback" in res["reasoning"] or "AI 통신 장애" in res["reasoning"]
