from agents.data_config import build_weight_map, get_demand_impact_score

def test_build_weight_map():
    wmap = build_weight_map()
    assert len(wmap) > 0
    assert "물류 파업" in wmap
    assert wmap["물류 파업"]["weight"] == 0.92

def test_get_demand_impact_score():
    res = get_demand_impact_score(["물류 파업", "마스크 품절", "없는키워드"])
    assert res["matched_count"] == 2
    assert "composite_score" in res
    assert len(res["affected_lag_items"]) == 2
