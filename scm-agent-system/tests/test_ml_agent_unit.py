# tests/test_ml_agent_unit.py
import pytest
import numpy as np
from agents.ml_agent import cosine_similarity, SchemaMappingRequest, map_schema

def test_cosine_similarity_edge_cases():
    # Test identical vectors
    v1 = np.array([1.0, 2.0, 3.0])
    v2 = np.array([1.0, 2.0, 3.0])
    assert pytest.approx(cosine_similarity(v1, v2)) == 1.0

    # Test orthogonal vectors
    v3 = np.array([1.0, 0.0])
    v4 = np.array([0.0, 1.0])
    assert pytest.approx(cosine_similarity(v3, v4)) == 0.0

    # Test opposite vectors
    v5 = np.array([1.0, -1.0])
    v6 = np.array([-1.0, 1.0])
    assert pytest.approx(cosine_similarity(v5, v6)) == -1.0

    # Test zero vector fallback
    v7 = np.array([0.0, 0.0, 0.0])
    assert cosine_similarity(v7, v1) == 0.0

def test_schema_mapping_exact_alias():
    # Verify deterministic alias lookup mapping
    req = SchemaMappingRequest(
        company_id="SIGMA",
        raw_headers=["지점", "품목", "수량", "날짜"],
        standard_columns=["region_code", "product_name", "quantity", "date"]
    )
    res = map_schema(req)
    assert res.mapping["지점"] == "region_code"
    assert res.mapping["품목"] == "product_name"
    assert res.mapping["수량"] == "quantity"
    assert res.mapping["날짜"] == "date"
    assert res.mapping_confidence["지점"] == 1.0
