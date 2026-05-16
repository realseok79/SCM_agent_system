from agents.data_agent import DataAgent

def test_fetch_inventory_data():
    agent = DataAgent()
    data = agent.fetch_inventory_data()
    assert "item" in data
    assert "stock" in data
