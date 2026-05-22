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

def test_parse_weather_score_dict_input():
    """weather_text가 딕셔너리로 제공될 때 GTS 악천후 지수 파싱 및 강수량 기반 폴백 기능 검증"""
    scorer = LogisticsRiskScorer()
    
    # 1. weather_desc 또는 raw_text가 존재하는 경우
    assert scorer.parse_weather_score({"weather_desc": "Heavy rain"}) == 5.5
    assert scorer.parse_weather_score({"raw_text": "Typhoon"}) == 8.5
    
    # 2. weather_desc/raw_text가 없거나 비어 있고 강수량(precipitation)만 존재하는 경우
    assert scorer.parse_weather_score({"precipitation": 20.0}) == 5.5  # Heavy rain (>15.0)
    assert scorer.parse_weather_score({"precipitation": 5.0}) == 2.5   # Rain (>0.0)
    assert scorer.parse_weather_score({"precipitation": 0.0}) == 0.0   # Clear (else)
    assert scorer.parse_weather_score({"weather_desc": None, "raw_text": None, "precipitation": 0.0}) == 0.0

def test_iot_health_and_port_congestion_penalties():
    """창고 IoT 건강도 하락 및 Spire Maritime 항만 혼잡도 증가에 따른 조달 지연일 및 자연어 원인 가산 검증"""
    scorer = LogisticsRiskScorer()
    
    # 1. IoT 건강도 80점 미만 시 지연일 가산 검증 (80 - 60) / 20 = 1.0일 가산
    delay_iot = scorer.calculate_lead_time_delay(weather_score=0.0, prev_risk_score=10.0, iot_health_score=60.0)
    # 기본 매크로 지연: 25 * 0.2 * (0.2^2) = 0.2
    # 최종 지연: 0.2 + 1.0 = 1.2
    assert delay_iot == pytest.approx(1.2, abs=1e-5)
    
    # 2. 항만 혼잡도 페널티 검증 50 / 25 = 2.0일 가산
    delay_port = scorer.calculate_lead_time_delay(weather_score=0.0, prev_risk_score=10.0, port_congestion_score=50.0)
    # 최종 지연: 0.2 + 2.0 = 2.2
    assert delay_port == pytest.approx(2.2, abs=1e-5)
    
    # 3. score_all 연동 시 원인 문자열(extra_delay_reasons)이 코멘트에 정상 포함되는지 검증
    res = scorer.score_all(
        data_vector={"oil_change_pct": 0.0, "index_change_pct": 0.0, "fx_change_pct": 0.0, "inflation_rate": 2.0},
        weather_text="맑음",
        trend_score=0.0,
        gdelt_tone=0.0,
        iot_health_score=70.0,
        port_congestion_score=40.0
    )
    
    assert "창고 IoT 장비 이상 감지" in res["delay_comment"]
    assert "항만 혼잡도 상승" in res["delay_comment"]
    assert "원인:" in res["delay_comment"]

def test_yaml_load_exception_handling(monkeypatch):
    """YAML 의사결정 규칙 파일 로딩 시 예외가 발생하더라도 정상적으로 Fallback 규칙으로 초기화되는지 검증"""
    import builtins
    import os
    
    # open 함수가 예외를 발생시키도록 monkeypatch 적용
    def mock_open(*args, **kwargs):
        raise IOError("Mocked IO Error for test")
        
    monkeypatch.setattr(builtins, "open", mock_open)
    
    # rules_path가 존재한다고 강제 설정하기 위해 os.path.exists 패치
    monkeypatch.setattr(os.path, "exists", lambda path: True if "decision_rules.yaml" in path else False)
    
    # 예외 발생 시점 검증
    scorer = LogisticsRiskScorer()
    assert len(scorer.rules) == 3
    assert scorer.rules[0]["action_code"] == "INCREASE_STOCK_20"

