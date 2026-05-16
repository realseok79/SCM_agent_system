from agents.analysis_agent import AnalysisAgent

def test_analyze_demand():
    agent = AnalysisAgent()
    result = agent.analyze_demand({"item": "test", "stock": 10})
    assert "forecast" in result
