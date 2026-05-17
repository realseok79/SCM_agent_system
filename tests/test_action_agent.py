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
