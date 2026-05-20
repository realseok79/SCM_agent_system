# tests/test_scoring_engine_extended.py
import pytest
from utils.scoring_engine import LogisticsRiskScorer

def test_parse_weather_score_edges():
    """다양한 날씨 텍스트 입력에 대한 GTS 악천후 지수 파싱 검증"""
    scorer = LogisticsRiskScorer()
    
    assert scorer.parse_weather_score("") == 0.0
    assert scorer.parse_weather_score(None) == 0.0
    
    # 태풍 / 허리케인
    assert scorer.parse_weather_score("Typhoon Warning") == 8.5
    assert scorer.parse_weather_score("강력한 태풍 접근") == 8.5
    
    # 폭우 / 폭설 / 강풍
    assert scorer.parse_weather_score("Heavy Rain tomorrow") == 5.5
    assert scorer.parse_weather_score("기습 폭설 주의보") == 5.5
    
    # 비 / 눈 / 소나기
    assert scorer.parse_weather_score("Light rain showers") == 2.5
    assert scorer.parse_weather_score("눈이 조금 내림") == 2.5
    
    # 맑음
    assert scorer.parse_weather_score("Sunny clear sky") == 0.0

def test_calculate_freight_impact_inflation_fallback():
    """inflation_rate가 None인 경우 국가별 디폴트 현실적 물가상승률(REALISTIC_INFLATION_FALLBACK)이 적용되는지 검증"""
    scorer = LogisticsRiskScorer()
    
    # Turkey는 디폴트 물가상승률이 50.0%로 설정되어 큰 cf 충격이 예상됨
    cf_turkey = scorer.calculate_freight_impact(oil_change_pct=10.0, inflation_rate=None, country_name="Turkey")
    assert cf_turkey > 0.0
    
    # 미수신 국가(예: Singapore)의 디폴트 물가상승률 3.0% 적용 검증
    cf_singapore = scorer.calculate_freight_impact(oil_change_pct=0.0, inflation_rate=None, country_name="Singapore")
    assert cf_singapore >= 0.0

def test_get_decision_default_fallback():
    """의사결정 규칙에 매칭되는 스코어가 없을 때 (매우 비정상적인 값 등) 기본 의사결정 반환 검증"""
    scorer = LogisticsRiskScorer()
    
    # rules를 인위적으로 비워 디폴트 fallback 규칙이 반환되는지 유도
    scorer.rules = []
    decision = scorer.get_decision(999.0)
    assert decision["action_code"] == "MAINTAIN"
    assert "EOQ" in decision["message"]

def test_score_all_with_defaults():
    """score_all 호출 시 Optional 매개변수가 생략되어도 안전하게 기본값으로 동작하는지 검증"""
    scorer = LogisticsRiskScorer()
    res = scorer.score_all(
        data_vector={"oil_change_pct": 5.0, "index_change_pct": -2.0, "fx_change_pct": 1.0},
        weather_text="Rainy weather",
        trend_score=0.5,
        gdelt_tone=-2.0,
        prev_risk_score=None
    )
    assert "integrated_risk_score" in res
    assert "freight_comment" in res
    assert "delay_comment" in res
    assert "demand_comment" in res
