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
    # alpha * ((10 - 5) / 5) * 100 = 0.4 * 1.0 * 100 = 40.0%
    assert cf_oil == pytest.approx(40.0, abs=1e-5)
    
    # 인플레이션 상승 상황 (연속 램프 반영)
    cf_inf = scorer.calculate_freight_impact(oil_change_pct=0.0, inflation_rate=5.0)
    # delta_I = 5.0 - 2.0 = 3.0
    # beta * ((delta_I - sigma_I) / sigma_I) * 100 = 0.6 * ((3.0 - 1.5) / 1.5) * 100 = 60.0%
    assert cf_inf == pytest.approx(60.0, abs=1e-5)

def test_calculate_demand_shock():
    scorer = LogisticsRiskScorer()
    
    # 기본 정상 상황
    ds = scorer.calculate_demand_shock(index_change_pct=0.0, fx_change_pct=0.0, social_score=0.0)
    assert ds == pytest.approx(0.0, abs=1e-5)
    
    # 주가지수 상승 상황 (Ds > 0, 클리핑 한계인 20.0 미만 상황으로 검증)
    ds_up = scorer.calculate_demand_shock(index_change_pct=3.0, fx_change_pct=0.0, social_score=0.0)
    # gamma * ln(1 + 0.03) * 100 = 5.0 * 0.0295588 * 100 = 14.78% (내부 2자리 반올림에 의해 정확히 14.78)
    assert ds_up == 14.78
    
    # 주가지수 하락 + 환율 폭등 + 사회 리스크 극심 상황
    ds_down = scorer.calculate_demand_shock(index_change_pct=-10.0, fx_change_pct=10.0, social_score=80.0)
    assert ds_down < 0.0

def test_calculate_lead_time_delay():
    scorer = LogisticsRiskScorer()
    
    # 날씨 무난, 매크로 안정 (prev_risk_score = 10.0 => M = 0.2 <= 1.0 이므로 macro_term = 0.0)
    assert scorer.calculate_lead_time_delay(weather_score=0.0, prev_risk_score=10.0) == 0.0
    
    # 기상 악화 반영 (Banker's Rounding 등의 플랫폼별 반올림 모호성 제거를 위해 9.0점 기준으로 검증)
    delay = scorer.calculate_lead_time_delay(weather_score=9.0, prev_risk_score=10.0)
    # lambda1 * 9.0 + 0 = 0.3 * 9.0 = 2.7 -> Exactly 2.7
    assert delay == pytest.approx(2.7, abs=1e-5)

def test_calculate_integrated_risk_score():
    scorer = LogisticsRiskScorer()
    
    # 모든 리스크가 극소화된 정상 상태 (Zero-baseline Shifted 시그모이드에 의해 X=0 이면 R_total = 0.0% 가 됨)
    r_normal = scorer.calculate_integrated_risk_score(cf=0.0, ds=0.0, lt_delay=0.0)
    assert r_normal == 0.0
    
    # 극단적 위기 상태
    r_crisis = scorer.calculate_integrated_risk_score(cf=80.0, ds=-50.0, lt_delay=5.0)
    # X = 1.5 * 80 + 1.5 * 50 + 5.0 * 5 = 120 + 75 + 25 = 220
    # Sigmoid(220) = 0.96265, Sigmoid(0) = 0.09531
    # R_scaled = 100 * (0.96265 - 0.09531) / (1.0 - 0.09531) ≈ 95.87% (반올림 시 95.9%)
    assert r_crisis == pytest.approx(95.9, abs=1e-1)
    assert r_crisis > 95.0

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
