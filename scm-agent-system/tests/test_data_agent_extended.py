# tests/test_data_agent_extended.py
import pytest
import os
import pandas as pd
from unittest.mock import MagicMock, patch
from agents.data_agent import GlobalIssueTracker, DataAgent
from dto.schemas import RiskCategory

@pytest.fixture
def mock_scm_data(tmp_path, monkeypatch):
    """더미 SCM 데이터 파일 생성 및 경로 설정"""
    scm_file = tmp_path / "scm_dummy.json"
    dummy_data = [
        {
            "day": 1,
            "daily_demand": 120.0,
            "holding_cost_per_unit": 0.5,
            "stockout_cost_per_unit": 10.0,
            "order_fixed_cost": 200.0,
            "item_name": "Part_A"
        }
    ]
    import json
    scm_file.write_text(json.dumps(dummy_data))
    monkeypatch.setattr("agents.data_agent.DATA_PATH", str(scm_file))
    return scm_file

def test_gdelt_tracker_api_exception():
    """GDELT API가 타임아웃 또는 Connection Error를 던질 때, 안전하게 Low 리스크와 0.0 톤으로 폴백하는지 검증"""
    tracker = GlobalIssueTracker()
    
    with patch("requests.get") as mock_get:
        mock_get.side_effect = Exception("GDELT API Timeout")
        res = tracker.fetch_supply_chain_risk_tone()
        
    assert res["risk_level"] == "Low"
    assert res["average_tone"] == 0.0
    assert res["article_count"] == 0

def test_data_agent_trends_api_429_recovery(mock_scm_data):
    """구글 트렌드 API(pytrends)에서 429 Too Many Requests가 발생했을 때 시뮬레이션 폴백이 가동되어 0.0 composite_score를 보장하는지 검증"""
    agent = DataAgent()
    
    with patch.object(agent._pytrends, "build_payload") as mock_build:
        mock_build.side_effect = Exception("429 Too Many Requests")
        res = agent._fetch_trend_signal()
        
    assert res["composite_score"] == 0.0
    assert res["matched_count"] == 0

def test_parse_unstructured_input_dataframe():
    """업로드된 엑셀/CSV 데이터프레임 형식의 비정형 입력에서 정형 수량과 품목명이 올바르게 파싱되는지 검증"""
    agent = DataAgent()
    df = pd.DataFrame([{"품목명": "고성능 MCU 칩", "수량": 350.0}])
    
    res = agent.parse_unstructured_input(file_df=df)
    assert res["item_name"] == "고성능 MCU 칩"
    assert res["quantity"] == 350.0
    assert res["category"] == RiskCategory.TECH_AND_SEMICONDUCTOR

def test_parse_unstructured_input_natural_language_mcu():
    """자연어 줄글 텍스트(예: 메모장 복사 붙여넣기)에서 품목명(반도체/칩), 수량(정규식)이 올바르게 추출되는지 검증"""
    agent = DataAgent()
    nl_text = "이번 주 대만 지진 영향으로 긴급하게 고성능 반도체 칩 250개(ea) 추가 확보 요망"
    
    res = agent.parse_unstructured_input(text=nl_text)
    assert "반도체" in res["item_name"] or "MCU" in res["item_name"]
    assert res["quantity"] == 250.0
    assert res["category"] == RiskCategory.TECH_AND_SEMICONDUCTOR

def test_parse_unstructured_input_natural_language_mask():
    """보건용 마스크 등 웰빙 품목 자연어 텍스트 파싱 및 카테고리 기상/기후 분류 매핑 검증"""
    agent = DataAgent()
    nl_text = "미세먼지 경보 발령 대비 보건용 마스크 1000개 수배 요망"
    
    res = agent.parse_unstructured_input(text=nl_text)
    assert "마스크" in res["item_name"]
    assert res["quantity"] == 1000.0
    assert res["category"] == RiskCategory.WEATHER_AND_CLIMATE

def test_parse_unstructured_input_empty():
    """빈 입력 또는 파싱 실패 시 기본 미분류 폴백 검증"""
    agent = DataAgent()
    res = agent.parse_unstructured_input()
    assert res["item_name"] == "미분류 아이템"
    assert res["quantity"] == 0.0
    assert res["category"] == RiskCategory.UNCLASSIFIED
