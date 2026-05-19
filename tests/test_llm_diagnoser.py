# tests/test_llm_diagnoser.py
from agents.llm_diagnoser import generate_action_plan

def test_generate_action_plan_fallback(monkeypatch):
    # Ensure OPENAI_API_KEY is not set to test the fallback mechanism
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    
    base_msg = "안전 재고 수준을 평소보다 15% 상향 조정하십시오."
    plan = generate_action_plan(
        region_name="Seoul Hub",
        product_name="Mask",
        delay_days=3.5,
        demand_shock=15.0,
        action_code="REORDER_UP_15",
        base_message=base_msg
    )
    
    assert plan == base_msg
