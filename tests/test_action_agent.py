from agents.action_agent import ActionAgent
from dto.schemas import InventorySignalDTO, AlertLevel

def test_execute_returns_result():
    agent = ActionAgent()
    signal = InventorySignalDTO(
        timestamp="2026-01-01T00:00:00",
        day=1,
        safety_stock=100.0,
        reorder_point=150.0,
        optimal_order_qty=300.0,
        confidence_level=0.95,
        alert_level=AlertLevel.WARNING
    )
    result = agent.execute(signal)
    assert result["day"] == 1
    assert result["approved_qty"] == 300.0
    assert result["action"] == "ORDER_EXECUTED"

def test_action_agent_guardrails_and_publish():
    agent = ActionAgent()
    
    # 1. Test negative quantity guardrail
    is_safe, reason = agent.validate_guardrails("Test SKU", -50.0)
    assert is_safe is False
    assert "올바르지 않습니다" in reason
    
    # 2. Test excessive capacity guardrail
    is_safe, reason = agent.validate_guardrails("Test SKU", 999999.0)
    assert is_safe is False
    assert "초과" in reason
    
    # 3. Test safe guardrail
    is_safe, reason = agent.validate_guardrails("Test SKU", 250.0)
    assert is_safe is True
    assert "통과" in reason
    
    # 4. Test execute_and_publish with invalid qty
    res_reject = agent.execute_and_publish("Test SKU", -10.0, "TECH_AND_SEMICONDUCTOR")
    assert res_reject["status"] == "REJECTED"
    
    # 5. Test execute_and_publish with valid qty
    res_approve = agent.execute_and_publish("Test SKU", 250.0, "TECH_AND_SEMICONDUCTOR")
    assert res_approve["status"] == "APPROVED"
    assert "order_id" in res_approve
    assert res_approve["data"]["item_name"] == "Test SKU"
    assert res_approve["data"]["order_qty"] == 250.0
