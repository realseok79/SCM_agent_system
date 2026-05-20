# tests/test_weather_connector.py
import os
import pytest
import datetime
import pandas as pd
import sqlite3
from unittest.mock import MagicMock, patch
from db import get_db_connection, init_db
from utils.connectors.weather_connector import (
    get_live_weather_by_station,
    load_wmo_master,
    get_seeded_mock_weather,
    fetch_live_weather,
    get_weather_for_region
)

@pytest.fixture(autouse=True)
def setup_db(monkeypatch):
    test_db = "data/test_weather_db.db"
    monkeypatch.setattr("db.DB_PATH", test_db)
    
    if os.path.exists(test_db):
        try:
            os.remove(test_db)
            if os.path.exists(test_db + "-wal"):
                os.remove(test_db + "-wal")
            if os.path.exists(test_db + "-shm"):
                os.remove(test_db + "-shm")
        except PermissionError:
            pass
            
    init_db()
    yield
    
    if os.path.exists(test_db):
        try:
            os.remove(test_db)
            if os.path.exists(test_db + "-wal"):
                os.remove(test_db + "-wal")
            if os.path.exists(test_db + "-shm"):
                os.remove(test_db + "-shm")
        except PermissionError:
            pass

@patch("requests.get")
def test_get_live_weather_by_station_without_key(mock_get):
    with patch.dict(os.environ, {"KMA_API_KEY": ""}):
        res = get_live_weather_by_station(108)
        assert "Mock Station 108" in res
        mock_get.assert_not_called()

@patch("requests.get")
def test_get_live_weather_by_station_with_key_success(mock_get):
    with patch.dict(os.environ, {"KMA_API_KEY": "testkey"}):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "GTS Weather Report Info"
        mock_get.return_value = mock_response
        
        res = get_live_weather_by_station(108)
        assert res == "GTS Weather Report Info"

@patch("requests.get")
def test_get_live_weather_by_station_with_key_api_error(mock_get):
    with patch.dict(os.environ, {"KMA_API_KEY": "testkey"}):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "AUTH_ERROR invalid key"
        mock_get.return_value = mock_response
        
        res = get_live_weather_by_station(108)
        assert "기상청 API 에러" in res

@patch("requests.get")
def test_get_live_weather_by_station_server_error(mock_get):
    with patch.dict(os.environ, {"KMA_API_KEY": "testkey"}):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        res = get_live_weather_by_station(108)
        assert "서버 응답 에러" in res

@patch("requests.get")
def test_get_live_weather_by_station_exception(mock_get):
    with patch.dict(os.environ, {"KMA_API_KEY": "testkey"}):
        mock_get.side_effect = Exception("Connection Refused")
        res = get_live_weather_by_station(108)
        assert "API 연결 실패" in res

def test_load_wmo_master_exists_and_regenerate():
    # 1. Clear file if exists to trigger automatic generation (line 70-85)
    csv_path = "data/wmo_station_master.csv"
    if os.path.exists(csv_path):
        os.remove(csv_path)
    
    df = load_wmo_master()
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
    assert os.path.exists(csv_path)
    
    # Call again to cover line 87 (reading existing CSV)
    df2 = load_wmo_master()
    assert len(df2) == len(df)

def test_get_weather_for_region_fromisoformat_exception():
    # Setup custom mock datetime module to avoid global recursion error
    import datetime as real_datetime
    
    class MockDatetimeClass:
        @staticmethod
        def fromisoformat(s):
            raise ValueError("Mocked error")
            
        @staticmethod
        def strptime(s, f):
            return real_datetime.datetime.strptime(s, f)
            
        @staticmethod
        def now():
            return real_datetime.datetime.now()
            
    class MockDatetimeModule:
        datetime = MockDatetimeClass
        timedelta = real_datetime.timedelta
        timezone = real_datetime.timezone

    with patch("utils.connectors.weather_connector.datetime", MockDatetimeModule):
        region = "KR-41"
        today_str = real_datetime.datetime.now().strftime("%Y-%m-%d")
        
        # Seed cache miss -> fetches live (mock)
        weather1 = get_weather_for_region(region, today_str)
        assert "temp" in weather1
        
        # Seed cache hit -> fromisoformat throws ValueError -> falls back to strptime
        weather2 = get_weather_for_region(region, today_str)
        assert weather2["temp"] == weather1["temp"]

def test_get_weather_for_region_both_datetime_parse_fail():
    """fromisoformat와 strptime 모두 실패 시 updated_at=None으로 처리하여 캐시 신선도 체크를 생략하는지 검증 (line 223-224)"""
    import datetime as real_datetime
    
    class MockDatetimeClass:
        @staticmethod
        def fromisoformat(s):
            raise ValueError("Mocked fromisoformat error")
        
        @staticmethod
        def strptime(s, f):
            raise ValueError("Mocked strptime error")
        
        @staticmethod
        def now():
            return real_datetime.datetime.now()
    
    class MockDatetimeModule:
        datetime = MockDatetimeClass
        timedelta = real_datetime.timedelta
        timezone = real_datetime.timezone

    with patch("utils.connectors.weather_connector.datetime", MockDatetimeModule):
        region = "KR-42"
        today_str = real_datetime.datetime.now().strftime("%Y-%m-%d")
        
        # 1차 호출: 캐시 miss → 생성
        weather1 = get_weather_for_region(region, today_str)
        assert "temp" in weather1
        
        # 2차 호출: 캐시 있지만 날짜 파싱 모두 실패 → is_fresh=False → 재조회
        weather2 = get_weather_for_region(region, today_str)
        assert "temp" in weather2


def test_get_seeded_mock_weather():
    res = get_seeded_mock_weather("KR-11", "2026-01-15")
    assert "temp" in res
    
    res_fallback = get_seeded_mock_weather("KR-11", "invalid-date")
    assert "temp" in res_fallback

    res_jeju = get_seeded_mock_weather("KR-49", "2026-05-15")
    assert res_jeju["temp"] is not None

def test_get_seeded_mock_weather_snow_path():
    """numpy rng를 mock하여 기온 <= 0 + 강수 조건을 강제로 유발, Snow 분기 실행 검증 (line 123-125)"""
    mock_rng = MagicMock()
    mock_rng.normal.return_value = -5.0    # temp = -5.0 (빙점 이하 → Snow)
    # uniform 호출 순서: humidity(40~90) → precipitation(1~25)
    mock_rng.uniform.side_effect = [60.0, 8.0]
    mock_rng.random.return_value = 0.05    # precip_chance < 0.15 → 강수 발생
    
    with patch("numpy.random.default_rng", return_value=mock_rng):
        res = get_seeded_mock_weather("KR-11", "2026-01-15")
        assert res["weather_desc"] == "Snow"
        assert res["precipitation"] == 8.0
        assert res["temp"] == -5.0

def test_get_seeded_mock_weather_rain_humidity_path():
    """numpy rng를 mock하여 기온 > 0 + 강수 조건을 강제로 유발, Rain + 습도보정 분기 실행 검증 (line 127-129)"""
    mock_rng = MagicMock()
    mock_rng.normal.return_value = 15.0    # temp = 15.0 (빙점 초과 → Rain)
    # uniform 호출 순서: humidity(40~90) → precipitation(1~25)
    mock_rng.uniform.side_effect = [60.0, 5.0]
    mock_rng.random.return_value = 0.05    # precip_chance < 0.15 → 강수 발생
    
    with patch("numpy.random.default_rng", return_value=mock_rng):
        res = get_seeded_mock_weather("KR-11", "2026-05-15")
        assert res["weather_desc"] == "Rain"
        # humidity = min(100, 60 + 15) = 75.0
        assert res["humidity"] == 75.0
        assert res["precipitation"] == 5.0

@patch("requests.get")
def test_fetch_live_weather_past_date(mock_get):
    past_date = "2020-01-01"
    res = fetch_live_weather("KR-11", past_date)
    assert "temp" in res
    mock_get.assert_not_called()

@patch("requests.get")
def test_fetch_live_weather_today_without_key(mock_get):
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    with patch.dict(os.environ, {"OPENWEATHER_API_KEY": ""}):
        res = fetch_live_weather("KR-11", today_str)
        assert "temp" in res
        mock_get.assert_not_called()

@patch("requests.get")
def test_fetch_live_weather_unknown_region(mock_get):
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    with patch.dict(os.environ, {"OPENWEATHER_API_KEY": "testkey"}):
        res = fetch_live_weather("KR-XX", today_str)
        assert "temp" in res
        mock_get.assert_not_called()

@patch("requests.get")
def test_fetch_live_weather_today_with_key_success(mock_get):
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # Test with rain
    with patch.dict(os.environ, {"OPENWEATHER_API_KEY": "ow_key"}):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "main": {"temp": 24.5, "humidity": 55.0},
            "rain": {"1h": 2.5},
            "weather": [{"main": "Rain"}]
        }
        mock_get.return_value = mock_response
        res = fetch_live_weather("KR-11", today_str)
        assert res["precipitation"] == 2.5
        assert res["weather_desc"] == "Rain"

    # Test with snow
    with patch.dict(os.environ, {"OPENWEATHER_API_KEY": "ow_key"}):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "main": {"temp": -2.5, "humidity": 80.0},
            "snow": {"1h": 1.2},
            "weather": [{"main": "Snow"}]
        }
        mock_get.return_value = mock_response
        res = fetch_live_weather("KR-11", today_str)
        assert res["precipitation"] == 1.2
        assert res["weather_desc"] == "Snow"

@patch("requests.get")
def test_fetch_live_weather_api_exceptions(mock_get):
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    with patch.dict(os.environ, {"OPENWEATHER_API_KEY": "ow_key"}):
        mock_get.side_effect = Exception("OpenWeather API Error")
        res = fetch_live_weather("KR-11", today_str)
        assert "temp" in res

def test_get_weather_for_region_cache_miss_and_hit():
    region = "KR-11"
    past_date = "2026-05-10"
    
    weather1 = get_weather_for_region(region, past_date)
    assert "temp" in weather1
    
    weather2 = get_weather_for_region(region, past_date)
    assert weather2["temp"] == weather1["temp"]

@patch("utils.connectors.weather_connector.fetch_live_weather")
def test_get_weather_for_region_today_fresh_vs_stale(mock_fetch_live):
    region = "KR-26"
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # 1. Miss -> calls fetch_live_weather
    mock_fetch_live.return_value = {
        "temp": 18.0, "humidity": 50.0, "precipitation": 0.0, "weather_desc": "Clear"
    }
    
    weather1 = get_weather_for_region(region, today_str)
    assert weather1["temp"] == 18.0
    mock_fetch_live.assert_called_once()
    
    # Manually update database updated_at to current local time to fix timezone difference
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE weather_cache SET updated_at = ? WHERE region_code = ? AND date = ?",
        (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), region, today_str)
    )
    conn.commit()
    conn.close()

    # 2. Fresh cache (< 1 hour) -> does not call fetch_live_weather again
    mock_fetch_live.reset_mock()
    weather2 = get_weather_for_region(region, today_str)
    assert weather2["temp"] == 18.0
    mock_fetch_live.assert_not_called()

    # 3. Stale cache (> 1 hour) -> updates updated_at to 2 hours ago
    conn = get_db_connection()
    cursor = conn.cursor()
    two_hours_ago = (datetime.datetime.now() - datetime.timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "UPDATE weather_cache SET updated_at = ? WHERE region_code = ? AND date = ?",
        (two_hours_ago, region, today_str)
    )
    conn.commit()
    conn.close()

    mock_fetch_live.reset_mock()
    mock_fetch_live.return_value = {
        "temp": 19.5, "humidity": 45.0, "precipitation": 0.0, "weather_desc": "Clouds"
    }
    weather3 = get_weather_for_region(region, today_str)
    assert weather3["temp"] == 19.5
    mock_fetch_live.assert_called_once()

@patch("utils.connectors.weather_connector.get_db_connection")
def test_get_weather_for_region_db_exception(mock_get_db):
    # Cover the catch block for database upsert failures
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_get_db.return_value = mock_conn
    
    # Make select query pass but upsert fail
    mock_cursor.fetchone.return_value = None
    mock_cursor.execute.side_effect = [None, Exception("Mock Database Failure")]
    
    res = get_weather_for_region("KR-11", "2026-05-15")
    assert "temp" in res
    mock_conn.rollback.assert_called_once()
