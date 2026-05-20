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

def test_data_agent_duplicate_prevention_and_dynamic_sku(monkeypatch):
    from dto.schemas import DemandDTO
    agent = DataAgent()
    
    # 1. Mock DB record with custom SKU details to verify dynamic loading
    agent._db = [{
        "daily_demand": 120.0,
        "lead_time_days": 8.0,
        "item_id": "CUSTOM-ID-99",
        "item_name": "Premium Semiconductor Chip",
        "holding_cost_per_unit": 4.0,
        "stockout_cost_per_unit": 20.0,
        "weather_index": 1.0,
        "macro_trend": 1.0
    }]
    
    monkeypatch.setattr(agent, "_fetch_external_signals",
                        lambda day: {"weather_index": 1.0, "macro_trend": 1.0,
                                     "lead_time_days": 8.0, "stress_event": False})
    monkeypatch.setattr(agent, "_fetch_trend_signal",
                        lambda: {"composite_score": 0.4, "matched_count": 1})
                        
    # Call collect on day 1
    res1 = agent.collect(1, datetime.date.today(), {}, 300.0)
    assert len(agent._demand_history) == 1
    assert agent._demand_history[0] == 120.0
    assert agent.last_processed_day == 1
    
    # Verify collect_demand_dto on same day prevents duplicate history accumulation
    dto = agent.collect_demand_dto(1, datetime.date.today(), {}, 300.0)
    
    # Double-check that duplicate append was prevented!
    assert len(agent._demand_history) == 1
    assert len(agent._lt_history) == 1
    
    # Verify dynamic item details were successfully mapped
    assert isinstance(dto, DemandDTO)
    assert dto.item_id == "CUSTOM-ID-99"
    assert dto.item_name == "Premium Semiconductor Chip"
    assert dto.unit_cost == 4.0 / 0.2
    assert dto.demand_impact == 0.4

def test_parse_unstructured_input(monkeypatch):
    import pandas as pd
    from dto.schemas import RiskCategory
    agent = DataAgent()
    
    # 1. Ensure OPENAI_API_KEY is not set for deterministic fallback test
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    
    # 2. 자연어 텍스트 파싱 검증
    res_text = agent.parse_unstructured_input(text="반도체 칩 250개 입고")
    assert res_text["item_name"] == "고성능 반도체 칩(MCU)"
    assert res_text["quantity"] == 250.0
    assert res_text["category"] == RiskCategory.TECH_AND_SEMICONDUCTOR
    
    # 3. 엑셀 파일 DataFrame 파싱 검증
    df = pd.DataFrame([{"품목명": "메모리 모듈", "수량": 500}])
    res_df = agent.parse_unstructured_input(file_df=df)
    assert res_df["item_name"] == "메모리 모듈"
    assert res_df["quantity"] == 500.0
    assert res_df["category"] == RiskCategory.TECH_AND_SEMICONDUCTOR

def test_parse_unstructured_input_with_llm(monkeypatch):
    from dto.schemas import RiskCategory
    agent = DataAgent()
    monkeypatch.setenv("OPENAI_API_KEY", "mock-key")
    
    class MockParsed:
        item_name = "테스트 반도체"
        quantity = 330.0
        category = "TECH_AND_SEMICONDUCTOR"
        
    class MockMessage:
        parsed = MockParsed()
        
    class MockChoice:
        message = MockMessage()
        
    class MockCompletion:
        choices = [MockChoice()]
        
    class MockChatCompletions:
        def parse(self, *args, **kwargs):
            return MockCompletion()
            
    class MockChat:
        completions = MockChatCompletions()
        
    class MockBeta:
        chat = MockChat()
        
    class MockOpenAI:
        def __init__(self, *args, **kwargs):
            self.beta = MockBeta()
            
    monkeypatch.setattr("openai.OpenAI", MockOpenAI)
    
    res = agent.parse_unstructured_input(text="임의의 자연어 텍스트")
    assert res["item_name"] == "테스트 반도체"
    assert res["quantity"] == 330.0
    assert res["category"] == RiskCategory.TECH_AND_SEMICONDUCTOR

