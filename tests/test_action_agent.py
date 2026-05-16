from agents.action_agent import ActionAgent

def test_execute_order():
    agent = ActionAgent()
    result = agent.execute_order({"forecast": 100})
    assert "order_id" in result
