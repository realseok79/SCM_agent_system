# tests/test_background_worker_extended.py
import pytest
import os
import json
from unittest.mock import patch, MagicMock
import db
from utils.background_worker import get_active_countries, run_worker
import utils.background_worker

TEST_BG_DB_PATH = "data/test_bg_worker.db"

@pytest.fixture(autouse=True)
def setup_bg_db(monkeypatch):
    monkeypatch.setattr("db.DB_PATH", TEST_BG_DB_PATH)
    for suffix in ["", "-wal", "-shm"]:
        path = TEST_BG_DB_PATH + suffix
        if os.path.exists(path):
            try:
                os.remove(path)
            except PermissionError:
                pass
    
    db.init_db()
    yield
    
    for suffix in ["", "-wal", "-shm"]:
        path = TEST_BG_DB_PATH + suffix
        if os.path.exists(path):
            try:
                os.remove(path)
            except PermissionError:
                pass

def test_get_active_countries_kr():
    """KR- 코드가 South Korea로 매핑되는지 검증"""
    conn = db.get_db_connection()
    conn.execute("INSERT OR IGNORE INTO regions (region_name, region_code) VALUES ('Seoul', 'KR-11')")
    conn.commit()
    conn.close()
    
    result = get_active_countries()
    assert "South Korea" in result

def test_get_active_countries_multiple():
    """복수 국가 코드 매핑 검증"""
    conn = db.get_db_connection()
    conn.execute("INSERT OR IGNORE INTO regions (region_name, region_code) VALUES ('Seoul', 'KR-11')")
    conn.execute("INSERT OR IGNORE INTO regions (region_name, region_code) VALUES ('New York', 'US-NY')")
    conn.execute("INSERT OR IGNORE INTO regions (region_name, region_code) VALUES ('Beijing', 'CN-11')")
    conn.execute("INSERT OR IGNORE INTO regions (region_name, region_code) VALUES ('Tokyo', 'JP-13')")
    conn.execute("INSERT OR IGNORE INTO regions (region_name, region_code) VALUES ('London', 'GB-LND')")
    conn.commit()
    conn.close()
    
    result = get_active_countries()
    assert "South Korea" in result
    assert "United States" in result
    assert "China" in result
    assert "Japan" in result
    assert "United Kingdom" in result

def test_get_active_countries_no_regions():
    """지역이 없으면 기본값 South Korea 반환"""
    result = get_active_countries()
    assert result == ["South Korea"]

def test_get_active_countries_db_error(monkeypatch):
    """DB 오류 시 기본값 South Korea 반환"""
    monkeypatch.setattr("utils.background_worker.get_db_connection", MagicMock(side_effect=Exception("DB down")))
    result = get_active_countries()
    assert result == ["South Korea"]

@patch("utils.background_worker.get_live_weather_by_station")
@patch("utils.background_worker.GlobalMacroEngine")
@patch("utils.background_worker.GlobalIssueTracker")
@patch("utils.background_worker.DataAgent")
@patch("utils.background_worker.load_lkv")
@patch("utils.background_worker.save_lkv")
@patch("time.sleep")
def test_run_worker_orchestration_cycle(
    mock_sleep,
    mock_save_lkv,
    mock_load_lkv,
    mock_data_agent,
    mock_issue_tracker,
    mock_macro_engine,
    mock_weather,
    monkeypatch
):
    """
    [Background Worker Orchestration Loop 격리 검증]
    _keep_running 플래그와 time.sleep mock을 사용하여 백그라운드 워커의 수집 주기 오케스트레이션이
    외부 날씨, 매크로 엔진, GDELT, Google Trends 정보를 종합적으로 수집하고 
    LKV(최신 데이터 저장소)에 원자적으로 반영한 뒤 교착상태 없이 우아하게 정지하는지 검증합니다.
    """
    # 1. 시딩 및 모킹 설정
    conn = db.get_db_connection()
    conn.execute("INSERT OR IGNORE INTO regions (region_name, region_code) VALUES ('Seoul', 'KR-11')")
    conn.commit()
    conn.close()
    
    mock_load_lkv.return_value = {}
    mock_weather.return_value = {"temp": 20.0, "weather_desc": "Clear"}
    
    macro_instance = mock_macro_engine.return_value
    macro_instance.fetch_unified_macro_vector.return_value = {"oil_change_pct": 1.5}
    
    issue_instance = mock_issue_tracker.return_value
    issue_instance.fetch_supply_chain_risk_tone.return_value = {"risk_level": "Low", "average_tone": 0.0}
    
    agent_instance = mock_data_agent.return_value
    agent_instance._fetch_trend_signal.return_value = {"composite_score": 0.3}
    
    # 2. 루프 제어: 1회 루프 반복 직후 바로 정지시키기 위해, load_lkv 호출 시 플래그를 False로 전환
    def load_lkv_side_effect():
        utils.background_worker._keep_running = False
        return {}
    mock_load_lkv.side_effect = load_lkv_side_effect
    
    # 가동
    utils.background_worker._keep_running = True
    run_worker()
    
    # 3. 종합 데이터 수집 연동 확인
    assert mock_load_lkv.called
    assert mock_weather.called
    assert macro_instance.fetch_unified_macro_vector.called
    assert issue_instance.fetch_supply_chain_risk_tone.called
    assert agent_instance._fetch_trend_signal.called
    
    # 4. 저장성 검증
    assert mock_save_lkv.called
    saved_state = mock_save_lkv.call_args[0][0]
    assert "South Korea" in saved_state
    assert saved_state["South Korea"]["weather"] == {"temp": 20.0, "weather_desc": "Clear"}
    assert saved_state["South Korea"]["macro"] == {"oil_change_pct": 1.5}
    assert saved_state["South Korea"]["gdelt"] == {"risk_level": "Low", "average_tone": 0.0}
    assert saved_state["South Korea"]["trends"] == {"composite_score": 0.3}
