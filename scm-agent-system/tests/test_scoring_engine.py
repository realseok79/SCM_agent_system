import pytest
from utils.scoring_engine import LogisticsRiskScorer

def test_parse_weather_score():
    scorer = LogisticsRiskScorer()
    
    # 태풍 감지
    assert scorer.parse_weather_score("Typhoon warning in southern regions") == 8.5
    assert scorer.parse_weather_score("태풍 예보가 있습니다") == 8.5
    
    # 폭풍/폭설/폭우 감지
    assert scorer.parse_weather_score("Heavy rain causing localized flooding") == 5.5
    assert scorer.parse_weather_score("폭우 경보 발령") == 5.5
    
    # 일반 비/눈 감지
    assert scorer.parse_weather_score("Light rain showers expected in the afternoon") == 2.5
    assert scorer.parse_weather_score("비가 조금 오겠습니다") == 2.5
    
    # 맑음/정상
    assert scorer.parse_weather_score("Clear skies and sunny weather") == 0.0
    assert scorer.parse_weather_score(None) == 0.0

def test_calculate_freight_impact():
    scorer = LogisticsRiskScorer()
    
    # 기본 변동 없음 상황
    cf = scorer.calculate_freight_impact(oil_change_pct=0.0, inflation_rate=2.0)
    assert cf == 0.0
    
    # WTI 유가 상승 상황 (연속 램프 반영)
    cf_oil = scorer.calculate_freight_impact(oil_change_pct=10.0, inflation_rate=2.0)
    # alpha * (10 / 5) * 100 = 0.4 * 2.0 * 100 = 80.0%
    assert cf_oil == pytest.approx(80.0, abs=1e-5)
    
    # 인플레이션 상승 상황 (연속 램프 반영)
    cf_inf = scorer.calculate_freight_impact(oil_change_pct=0.0, inflation_rate=5.0)
    # beta * ((5.0 - 2.0) / 1.5) * 100 = 0.6 * 2.0 * 100 = 120.0% -> Clipped to 100.0%
    assert cf_inf == pytest.approx(100.0, abs=1e-5)

def test_calculate_demand_shock():
    scorer = LogisticsRiskScorer()
    
    # 기본 정상 상황
    ds = scorer.calculate_demand_shock(index_change_pct=0.0, fx_change_pct=0.0, social_score=0.0)
    assert ds == pytest.approx(0.0, abs=1e-5)
    
    # 주가지수 상승 상황 (Ds > 0, 클리핑 한계인 20.0 미만 상황으로 검증)
    ds_up = scorer.calculate_demand_shock(index_change_pct=3.0, fx_change_pct=0.0, social_score=0.0)
    # gamma * ln(1 + 0.03) * 100 = 1.0 * 0.0295588 * 100 = 2.96%
    assert ds_up == 2.96
    
    # 주가지수 하락 + 환율 폭등 + 사회 리스크 극심 상황
    ds_down = scorer.calculate_demand_shock(index_change_pct=-10.0, fx_change_pct=10.0, social_score=80.0)
    assert ds_down < 0.0

def test_calculate_lead_time_delay():
    scorer = LogisticsRiskScorer()
    
    # 날씨 무난, 매크로 안정 (prev_risk_score = 10.0 => M = 0.2)
    # lt_delay = 0.0 + 25.0 * 0.2 * (0.2 ** 2) = 0.2
    assert scorer.calculate_lead_time_delay(weather_score=0.0, prev_risk_score=10.0) == 0.2
    
    # 기상 악화 반영
    delay = scorer.calculate_lead_time_delay(weather_score=9.0, prev_risk_score=10.0)
    # 0.3 * 9.0 + 0.2 = 2.9
    assert delay == pytest.approx(2.9, abs=1e-5)

def test_calculate_integrated_risk_score():
    scorer = LogisticsRiskScorer()
    
    # 모든 리스크가 극소화된 정상 상태 (Zero-baseline Shifted 시그모이드에 의해 X=0 이면 R_total = 0.0% 가 됨)
    r_normal = scorer.calculate_integrated_risk_score(cf=0.0, ds=0.0, lt_delay=0.0)
    assert r_normal == 0.0
    
    # 극단적 위기 상태
    r_crisis = scorer.calculate_integrated_risk_score(cf=80.0, ds=-50.0, lt_delay=5.0)
    # X = 1.5 * 80 + 1.5 * 50 + 5.0 * 5 = 120 + 75 + 25 = 220
    # Sigmoid(220) = 0.740774, Sigmoid(0) = 0.09531
    # R_scaled = 100 * (0.740774 - 0.09531) / (1.0 - 0.09531) ≈ 71.34% -> 71.3
    assert r_crisis == pytest.approx(71.3, abs=1e-1)
    assert r_crisis > 70.0

def test_score_all():
    scorer = LogisticsRiskScorer()
    data_vector = {
        "oil_change_pct": 5.0,
        "index_change_pct": -2.0,
        "fx_change_pct": 3.0,
        "inflation_rate": 3.5,
        "integrated_risk_score": 25.0
    }
    res = scorer.score_all(
        data_vector=data_vector,
        weather_text="TYPHOON warning with heavy snow",
        trend_score=0.4,
        gdelt_tone=-2.5
    )
    
    assert "freight_rate_change" in res
    assert "demand_shock_index" in res
    assert "lead_time_delay" in res
    assert "integrated_risk_score" in res
def test_score_all_contains_comments():
    """
    score_all 결과에 실무 직관 자연어 코멘트 필드가 모두 포함되고 비어있지 않은지 검증
    """
    scorer = LogisticsRiskScorer()
    data_vector = {
        "oil_change_pct": 0.0,
        "index_change_pct": 0.0,
        "fx_change_pct": 0.0,
        "inflation_rate": 2.0,
        "integrated_risk_score": 10.0
    }
    res = scorer.score_all(
        data_vector=data_vector,
        weather_text="맑음",
        trend_score=0.0,
        gdelt_tone=0.0
    )
    
    assert "freight_comment" in res
    assert "delay_comment" in res
    assert "demand_comment" in res
    
    assert len(res["freight_comment"]) > 0
    assert len(res["delay_comment"]) > 0
    assert len(res["demand_comment"]) > 0

def test_scenario_weather_crisis():
    """
    시나리오 A (기상이변): 강설/폭우/태풍 등 악천후 주입 시 조달 지연일 상승 및 경고 이모지 부분 매칭 검증
    """
    scorer = LogisticsRiskScorer()
    data_vector = {
        "oil_change_pct": 0.0,
        "index_change_pct": 0.0,
        "fx_change_pct": 0.0,
        "inflation_rate": 2.0,
        "integrated_risk_score": 10.0
    }
    
    # 폭우 및 강풍 예보 상황 주입
    res = scorer.score_all(
        data_vector=data_vector,
        weather_text="강풍을 동반한 기습적인 폭우 예보",
        trend_score=0.0,
        gdelt_tone=0.0
    )
    
    assert res["weather_score"] == 5.5
    assert res["lead_time_delay"] >= 1.5
    
    # Brittle Test 방지를 위한 부분 포함(Inclusion) 검증 적용
    assert "🚨" in res["delay_comment"] or "⚠️" in res["delay_comment"]
    assert "지연" in res["delay_comment"]

def test_scenario_market_crash():
    """
    시나리오 B (금융 및 대외 충격): 주가 급락 및 환율 폭등, 지정학적 리스크 융합 상황 검증
    """
    scorer = LogisticsRiskScorer()
    data_vector = {
        "oil_change_pct": 0.0,
        "index_change_pct": -12.0,  # 주가지수 폭락
        "fx_change_pct": 8.0,       # 환율 폭등
        "inflation_rate": 2.0,
        "integrated_risk_score": 10.0
    }
    
    # GDELT 지정학적 극단 위기 및 Trends 이슈 융합 상황
    res = scorer.score_all(
        data_vector=data_vector,
        weather_text="맑음",
        trend_score=0.8,
        gdelt_tone=-4.5
    )
    
    assert res["demand_shock_index"] <= -5.0
    assert "🚨" in res["demand_comment"]
    assert "소비수요가 평소 대비" in res["demand_comment"] or "둔화" in res["demand_comment"]

def test_scenario_oil_surge():
    """
    시나리오 C (유가 폭등 및 공급망 인플레이션): 유가 급등과 물가상승 상황 검증
    """
    scorer = LogisticsRiskScorer()
    data_vector = {
        "oil_change_pct": 25.0,     # WTI 유가 25% 급등
        "index_change_pct": 0.0,
        "fx_change_pct": 0.0,
        "inflation_rate": 6.5,      # 높은 인플레이션
        "integrated_risk_score": 10.0
    }
    
    res = scorer.score_all(
        data_vector=data_vector,
        weather_text="맑음",
        trend_score=0.0,
        gdelt_tone=0.0
    )
    
    assert res["freight_rate_change"] >= 15.0
    assert "🚨" in res["freight_comment"]
    assert "운임이" in res["freight_comment"] and "상승" in res["freight_comment"]

def test_scenario_all_stable():
    """
    시나리오 D (완전 안정): 모든 변수가 안정적이고 관리가 되고 있을 때 검증
    """
    scorer = LogisticsRiskScorer()
    data_vector = {
        "oil_change_pct": 0.0,
        "index_change_pct": 1.0,
        "fx_change_pct": 0.0,
        "inflation_rate": 2.0,
        "integrated_risk_score": 10.0
    }
    
    res = scorer.score_all(
        data_vector=data_vector,
        weather_text="맑음",
        trend_score=0.0,
        gdelt_tone=0.0
    )
    
    # 안정 코멘트 확인
    assert "✅" in res["freight_comment"]
    assert "✅" in res["delay_comment"]
    assert "✅" in res["demand_comment"]
    
    assert res["integrated_risk_score"] < 10.0

def test_comment_length_within_ui_limit():
    """
    Streamlit expander 내부 UI 레이아웃 붕괴를 방지하기 위해 생성된 코멘트가 각각 300자 이내인지 검증
    """
    scorer = LogisticsRiskScorer()
    
    # 다양한 극단 데이터 주입
    data_vector = {
        "oil_change_pct": 99.0,
        "index_change_pct": -90.0,
        "fx_change_pct": 99.0,
        "inflation_rate": 15.0,
        "integrated_risk_score": 90.0
    }
    
    res = scorer.score_all(
        data_vector=data_vector,
        weather_text="TYPHOON warning, heavy rain, gale, localized flood and storm",
        trend_score=1.0,
        gdelt_tone=-10.0
    )
    
    assert len(res["freight_comment"]) <= 300
    assert len(res["delay_comment"]) <= 300
    assert len(res["demand_comment"]) <= 300

def test_extreme_edge_values_no_crash():
    """
    비정상적이거나 극단적인 경계값 입력 시에도 나누기 0 등의 예외 크래시 없이 수학적 범위 내로 정상 연산 및 클리핑되는지 검증
    """
    scorer = LogisticsRiskScorer()
    
    # 1. 극단적으로 큰 양수 주입
    data_vector_huge = {
        "oil_change_pct": 999999.0,
        "index_change_pct": 999999.0,
        "fx_change_pct": 999999.0,
        "inflation_rate": 999999.0,
        "integrated_risk_score": 999999.0
    }
    
    res_huge = scorer.score_all(
        data_vector=data_vector_huge,
        weather_text="정상",
        trend_score=9999.0,
        gdelt_tone=-9999.0
    )
    
    # 클리핑 검증
    assert res_huge["freight_rate_change"] == 100.0  # +100% 클리핑
    assert res_huge["demand_shock_index"] <= 20.0    # +20% 클리핑
    assert res_huge["integrated_risk_score"] <= 100.0
    
    # 2. 극단적인 음수 주입
    data_vector_neg = {
        "oil_change_pct": -999999.0,
        "index_change_pct": -999999.0,
        "fx_change_pct": -999999.0,
        "inflation_rate": -999999.0,
        "integrated_risk_score": -999999.0
    }
    
    res_neg = scorer.score_all(
        data_vector=data_vector_neg,
        weather_text="",
        trend_score=-9999.0,
        gdelt_tone=9999.0
    )
    
    assert res_neg["freight_rate_change"] == 0.0     # 0% 클리핑
    assert res_neg["demand_shock_index"] == -100.0   # -100% 클리핑
    assert 0.0 <= res_neg["integrated_risk_score"] <= 100.0

def test_decision_rules():
    scorer = LogisticsRiskScorer()
    
    # 규칙 직접 테스트
    dec_high = scorer.get_decision(90)
    assert dec_high["action_code"] == "INCREASE_STOCK_20"
    assert dec_high["delay_days"] == 3.5
    
    dec_mid = scorer.get_decision(70)
    assert dec_mid["action_code"] == "PULL_FORWARD_1DAY"
    assert dec_mid["delay_days"] == 1.5
    
    dec_low = scorer.get_decision(30)
    assert dec_low["action_code"] == "MAINTAIN"
    assert dec_low["delay_days"] == 0.0

    # score_all 호출 결과 연동 확인
    data_vector = {
        "oil_change_pct": 20.0,
        "index_change_pct": -10.0,
        "fx_change_pct": 5.0,
        "inflation_rate": 5.0,
        "integrated_risk_score": 85.0
    }
    res = scorer.score_all(
        data_vector=data_vector,
        weather_text="TYPHOON warning",
        trend_score=0.9,
        gdelt_tone=-8.0
    )
    assert "decision_action_code" in res
    assert "decision_message" in res
    assert "decision_delay_days" in res
    assert res["decision_action_code"] == "INCREASE_STOCK_20"
