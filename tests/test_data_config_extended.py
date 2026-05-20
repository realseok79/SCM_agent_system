# tests/test_data_config_extended.py
import pytest
from agents.data_config import (
    build_weight_map,
    get_demand_impact_score,
    SCENARIO_KEYWORDS,
    KEYWORD_WEIGHT_MAP
)

def test_build_weight_map_completeness():
    """모든 카테고리의 고유 키워드가 weight_map에 빌드되는지 검증"""
    wmap = build_weight_map()
    # weight_map은 flat dict이므로 카테고리 간 중복 키워드(예: "소비자 신뢰지수 하락")는
    # 하나로 병합됩니다. 고유 키워드 수와 비교해야 합니다.
    all_keywords = set()
    for sides in SCENARIO_KEYWORDS.values():
        for keywords in sides.values():
            all_keywords.update(keywords.keys())
    assert len(wmap) == len(all_keywords)
    assert len(wmap) > 250  # v2.0에서 ~270개 이상의 고유 키워드

def test_build_weight_map_has_metadata():
    """빌드된 키워드에 category/side 메타데이터가 포함되는지 검증"""
    wmap = build_weight_map()
    for kw, meta in wmap.items():
        assert "weight" in meta
        assert "lag_days" in meta
        assert "direction" in meta
        assert "category" in meta
        assert "side" in meta

def test_get_demand_impact_score_threat_keywords():
    """위협 키워드 입력 시 음수 방향 스코어 반환"""
    result = get_demand_impact_score(["물류 파업", "항만 봉쇄"])
    assert result["composite_score"] < 0
    assert result["matched_count"] == 2

def test_get_demand_impact_score_opportunity_keywords():
    """기회 키워드 입력 시 양수 방향 스코어 반환"""
    result = get_demand_impact_score(["엔데믹", "보복 소비"])
    assert result["composite_score"] > 0
    assert result["matched_count"] == 2

def test_get_demand_impact_score_no_match():
    """매칭 키워드가 없을 때 composite_score=0, matched_count=0"""
    result = get_demand_impact_score(["비관련 키워드 XYZ123"])
    assert result["composite_score"] == 0.0
    assert result["matched_count"] == 0
    assert result["immediate_impact"] == 0.0

def test_get_demand_impact_score_immediate_vs_deferred():
    """lag_days=0 키워드와 lag_days>0 키워드 분류 검증"""
    result = get_demand_impact_score(["마스크 품절", "금리 인상"])
    # 마스크 품절: lag=0 (immediate), 금리 인상: lag=45 (deferred)
    assert result["immediate_impact"] != 0.0
    assert len(result["deferred_impact"]) >= 1
    assert result["deferred_impact"][0]["lag_days"] > 0

def test_get_demand_impact_score_empty_list():
    """빈 키워드 리스트 입력 시 기본값 반환"""
    result = get_demand_impact_score([])
    assert result["composite_score"] == 0.0
    assert result["matched_count"] == 0
