# tests/test_scheduler.py
import os
import sys
import sqlite3
import pytest
from unittest.mock import MagicMock, patch

# ── Streamlit 의존성 모킹 (pytest Import 시 크래시 방지) ──
mock_st = MagicMock()
def mock_decorator(*args, **kwargs):
    def decorator(func):
        return func
    return decorator
mock_st.cache_data = mock_decorator
mock_st.cache_resource = mock_decorator
sys.modules["streamlit"] = mock_st
sys.modules["streamlit_autorefresh"] = MagicMock()

# 테스트 데이터베이스 경로로 환경변수 재정의
TEST_DB_PATH = "data/test_scheduler.db"
os.environ["DB_PATH"] = TEST_DB_PATH

import db
db.DB_PATH = TEST_DB_PATH

from db import init_db, get_db_connection
from utils.scheduler import daily_llm_insight_batch

@pytest.fixture(autouse=True)
def setup_test_db():
    """
    각 테스트 실행 전 데이터베이스 스키마 생성 및 초기화
    """
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except PermissionError:
            pass
            
    init_db()
    yield
    
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except PermissionError:
            pass

def test_daily_llm_insight_batch_success():
    """
    daily_llm_insight_batch 실행 시, 각 지점의 외부 정보(LKV)를 바탕으로
    Scorer를 실행하고 LLM 처방을 DB에 정상적으로 UPSERT하는지 검증
    """
    # 1. 테스트용 가짜 LKV 데이터 모킹
    mock_lkv_data = {
        "South Korea": {
            "weather": "맑음, 기온 20도",
            "macro": {
                "oil_change_pct": 0.5,
                "inflation_rate": 2.5,
                "index_change_pct": -1.2,
                "fx_change_pct": 0.3
            },
            "gdelt": {
                "average_tone": -1.5,
                "risk_level": "Medium",
                "top_headline": "Supply chain disruption fears grow"
            },
            "trends": {
                "composite_score": 15.0,
                "matched_count": 5
            }
        }
    }
    
    # 2. 패치(Patch) 적용: load_lkv 및 generate_action_plan 모킹
    with patch("utils.scheduler.load_lkv", return_value=mock_lkv_data), \
         patch("utils.scheduler.generate_action_plan", return_value="**Mocked SCM Action Plan:** 발주량을 **15%** 증량하십시오."):
        
        # 배치 수행
        daily_llm_insight_batch()
        
    # 3. DB 검증
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT region_code, date, action_plan_msg FROM regional_insights")
    rows = cursor.fetchall()
    conn.close()
    
    # 4. 검증 단언 (Assertion)
    # db.py는 기본적으로 KR-11, KR-26, KR-49 지점을 시드하므로, 이 3개 지점의 AI 처방이 정상적으로 적재되어야 합니다.
    assert len(rows) == 3
    for row in rows:
        assert row["region_code"] in ["KR-11", "KR-26", "KR-49"]
        assert "**Mocked SCM Action Plan:**" in row["action_plan_msg"]
        assert "발주량을 **15%** 증량하십시오." in row["action_plan_msg"]
