# tests/test_scheduler_extended.py
import pytest
import os
from unittest.mock import patch, MagicMock
import db
from utils.scheduler import daily_weather_batch, daily_llm_insight_batch, start_scheduler

TEST_SCHED_DB_PATH = "data/test_scheduler.db"

@pytest.fixture(autouse=True)
def setup_scheduler_db(monkeypatch):
    monkeypatch.setattr("db.DB_PATH", TEST_SCHED_DB_PATH)
    for suffix in ["", "-wal", "-shm"]:
        path = TEST_SCHED_DB_PATH + suffix
        if os.path.exists(path):
            try:
                os.remove(path)
            except PermissionError:
                pass
    
    db.init_db()
    
    conn = db.get_db_connection()
    conn.execute("INSERT OR IGNORE INTO regions (region_name, region_code) VALUES ('Seoul', 'KR-11')")
    conn.execute("INSERT OR IGNORE INTO regions (region_name, region_code) VALUES ('Busan', 'KR-26')")
    conn.commit()
    conn.close()
    
    yield
    
    for suffix in ["", "-wal", "-shm"]:
        path = TEST_SCHED_DB_PATH + suffix
        if os.path.exists(path):
            try:
                os.remove(path)
            except PermissionError:
                pass

@patch("utils.scheduler.get_weather_for_region")
def test_daily_weather_batch_success(mock_weather):
    """날씨 배치가 각 지역에 대해 호출되는지 검증"""
    mock_weather.return_value = {"temp": 25.0, "weather_desc": "맑음", "humidity": 50}
    
    daily_weather_batch(force_refresh=False)
    
    assert mock_weather.call_count >= 2  # Seoul + Busan

@patch("utils.scheduler.get_weather_for_region")
def test_daily_weather_batch_force_refresh(mock_weather):
    """force_refresh=True 시 기존 캐시를 삭제하고 재호출"""
    mock_weather.return_value = {"temp": 20.0, "weather_desc": "흐림", "humidity": 70}
    
    daily_weather_batch(force_refresh=True)
    
    assert mock_weather.call_count >= 2

@patch("utils.scheduler.get_weather_for_region")
def test_daily_weather_batch_api_failure(mock_weather):
    """API 실패 시 배치가 중단되지 않고 계속 진행"""
    mock_weather.side_effect = Exception("API Timeout")
    
    # 에러가 발생해도 배치 자체는 중단되지 않아야 함
    daily_weather_batch(force_refresh=False)

@patch("utils.scheduler.generate_action_plan")
@patch("utils.scheduler.load_lkv")
def test_daily_llm_insight_batch(mock_lkv, mock_llm):
    """LLM 처방 배치가 각 지역에 대해 실행되는지 검증"""
    mock_lkv.return_value = {
        "South Korea": {
            "weather": "맑음",
            "macro": {"oil_change_pct": 1.0, "inflation_rate": 2.5, "index_change_pct": 0.5, "fx_change_pct": -0.3},
            "gdelt": {"average_tone": -1.5, "risk_level": "Medium", "top_headline": "Supply chain disruption"},
            "trends": {"composite_score": 0.3, "matched_count": 2}
        }
    }
    mock_llm.return_value = "테스트 AI 처방 메시지"
    
    daily_llm_insight_batch()
    
    assert mock_llm.call_count >= 2  # Seoul + Busan

@patch("utils.scheduler.generate_action_plan")
@patch("utils.scheduler.load_lkv")
def test_daily_llm_insight_batch_no_regions(mock_lkv, mock_llm, monkeypatch):
    """등록된 지역이 없을 때 스킵"""
    # 지역을 비우기
    conn = db.get_db_connection()
    conn.execute("DELETE FROM regions")
    conn.commit()
    conn.close()
    
    mock_lkv.return_value = {}
    daily_llm_insight_batch()
    
    mock_llm.assert_not_called()

@patch("utils.scheduler.daily_llm_insight_batch")
@patch("utils.scheduler.daily_weather_batch")
def test_start_scheduler(mock_weather_batch, mock_llm_batch):
    """스케줄러가 정상적으로 시작되고 초기 실행되는지 검증"""
    scheduler = start_scheduler()
    
    # 초기 실행 확인
    mock_weather_batch.assert_called_once()
    mock_llm_batch.assert_called_once()
    
    # 스케줄러 종료
    scheduler.shutdown()
