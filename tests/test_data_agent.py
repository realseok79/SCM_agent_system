import datetime
import numpy as np
from agents.data_agent import DataAgent, GlobalIssueTracker
from dto.schemas import DataDTO

def test_collect_returns_data_dto(monkeypatch):
    agent = DataAgent()
    agent._db = [{"daily_demand": 100.0, "lead_time_days": 7.0}]
    
    monkeypatch.setattr(agent, "_fetch_external_signals",
                        lambda day: {"weather_index": 1.1, "macro_trend": 1.2,
                                     "lead_time_days": 7.0, "stress_event": False})
    monkeypatch.setattr(agent, "_fetch_trend_signal",
                        lambda: {"composite_score": 0.5, "matched_count": 2})
                        
    result = agent.collect(1, datetime.date.today(), {}, 500.0)
    assert isinstance(result, DataDTO)
    assert result.daily_demand == 100.0
    assert result.current_stock == 500.0
    assert result.trend_composite_score == 0.5
    assert result.trend_matched_count == 2

def test_fix_missing():
    agent = DataAgent()
    # Empty history fallback
    assert agent._fix_missing(None, "daily_demand") == 100.0
    
    # History exists fallback
    agent._demand_history = [50.0, 60.0, 70.0]
    assert agent._fix_missing(None, "daily_demand") == 60.0
    
    # Valid value
    assert agent._fix_missing(120.0, "daily_demand") == 120.0

def test_clip_outlier():
    agent = DataAgent()
    # History length < 10
    assert agent._clip_outlier(1000.0, "daily_demand") == 1000.0
    
    # History length >= 10, check outlier clipping
    agent._demand_history = [100.0] * 30
    # Mean = 100, std = 0. Upper/lower limit = 100.0
    assert agent._clip_outlier(200.0, "daily_demand") == 100.0
    assert agent._clip_outlier(-50.0, "daily_demand") == 100.0

def test_fetch_external_signals_fallback(monkeypatch):
    agent = DataAgent()
    def mock_get_raise(*args, **kwargs):
        raise Exception("Connection failed")
    monkeypatch.setattr("requests.get", mock_get_raise)
    
    res = agent._fetch_external_signals(1)
    assert res["weather_index"] == 1.0
    assert res["lead_time_days"] == 7.0

def test_global_issue_tracker_success(monkeypatch):
    tracker = GlobalIssueTracker()
    
    class MockResponse:
        def __init__(self, status_code, json_data):
            self.status_code = status_code
            self.text = "has data"
            self.json_data = json_data
        def json(self):
            return self.json_data

    # Mock high risk articles
    mock_data = {
        "articles": [
            {"tone": -5.0, "title": "Headline 1"},
            {"tone": -4.0, "title": "Headline 2"}
        ]
    }
    monkeypatch.setattr("requests.get", lambda url, params, timeout: MockResponse(200, mock_data))
    res = tracker.fetch_supply_chain_risk_tone()
    assert res["risk_level"] == "High"
    assert res["article_count"] == 2
    assert res["top_headline"] == "Headline 1"

    # Mock no articles
    monkeypatch.setattr("requests.get", lambda url, params, timeout: MockResponse(200, {}))
    res = tracker.fetch_supply_chain_risk_tone()
    assert res["risk_level"] == "Low"

def test_data_agent_trend_fallback():
    agent = DataAgent()
    agent._pytrends = None
    res = agent._fetch_trend_signal()
    assert res == {"composite_score": 0.0, "matched_count": 0}
