# tests/test_background_worker.py
import os
import sqlite3
import json
import pytest
import datetime

from db import get_db_connection, init_db
from utils.background_worker import get_active_countries
from utils.state_manager import load_lkv, save_lkv

# 테스트용 DB 및 LKV 상태 파일 경로 재정의용 패치
TEST_DB_PATH = "data/test_background_worker.db"
TEST_LKV_PATH = "data/test_last_known_values.json"

@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """
    테스트 실행 전 격리된 테스트용 DB 및 LKV 상태 파일을 지정하고 패치합니다.
    """
    monkeypatch.setattr("db.DB_PATH", TEST_DB_PATH)
    monkeypatch.setattr("utils.background_worker.get_db_connection", get_db_connection)
    monkeypatch.setattr("utils.state_manager.STATE_FILE", TEST_LKV_PATH)
    
    # 1. DB 파일 클린업 및 초기화
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
            if os.path.exists(TEST_DB_PATH + "-wal"):
                os.remove(TEST_DB_PATH + "-wal")
            if os.path.exists(TEST_DB_PATH + "-shm"):
                os.remove(TEST_DB_PATH + "-shm")
        except PermissionError:
            pass
            
    init_db()
    
    # 2. DB 기본 시드 클리어 (동적 테스트를 위해 비움)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM regions")
    conn.commit()
    conn.close()
    
    # 3. LKV 임시 파일 클린업
    if os.path.exists(TEST_LKV_PATH):
        try:
            os.remove(TEST_LKV_PATH)
        except PermissionError:
            pass
            
    yield
    
    # 환경 정리
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
            if os.path.exists(TEST_DB_PATH + "-wal"):
                os.remove(TEST_DB_PATH + "-wal")
            if os.path.exists(TEST_DB_PATH + "-shm"):
                os.remove(TEST_DB_PATH + "-shm")
        except PermissionError:
            pass
            
    if os.path.exists(TEST_LKV_PATH):
        try:
            os.remove(TEST_LKV_PATH)
        except PermissionError:
            pass

def test_get_active_countries_empty_db():
    """
    DB에 활성화된 지역이 전혀 존재하지 않을 경우 기본값 'South Korea'를 반환하는지 검증
    """
    countries = get_active_countries()
    assert countries == ["South Korea"]

def test_get_active_countries_korea_only():
    """
    DB에 한국(KR) 지역만 등록되어 있을 경우 South Korea만 반환하는지 검증
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO regions (region_name, region_code, description) VALUES (?, ?, ?)", 
                   ("서울특별시", "KR-11", "서울 기지"))
    cursor.execute("INSERT INTO regions (region_name, region_code, description) VALUES (?, ?, ?)", 
                   ("부산광역시", "KR-26", "부산 허브"))
    conn.commit()
    conn.close()
    
    countries = get_active_countries()
    assert countries == ["South Korea"]

def test_get_active_countries_multi_country():
    """
    한국(KR), 미국(US), 일본(JP) 등 복수 국가가 regions에 등록되면 동적으로 대상에 포함되는지 검증
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO regions (region_name, region_code, description) VALUES (?, ?, ?)", 
                   ("서울특별시", "KR-11", "서울 기지"))
    cursor.execute("INSERT INTO regions (region_name, region_code, description) VALUES (?, ?, ?)", 
                   ("캘리포니아주", "US-CA", "미국 서부 기지"))
    cursor.execute("INSERT INTO regions (region_name, region_code, description) VALUES (?, ?, ?)", 
                   ("도쿄도", "JP-13", "일본 도쿄"))
    conn.commit()
    conn.close()
    
    countries = get_active_countries()
    
    assert len(countries) == 3
    assert "South Korea" in countries
    assert "United States" in countries
    assert "Japan" in countries

def test_get_active_countries_dynamic_switching():
    """
    워커 실행 중 DB에 지점이 동적으로 추가(해외 진출 등)되었을 때 감지 범위가 동적으로 늘어나는지 검증
    """
    # 1단계: 한국만 등록
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO regions (region_name, region_code, description) VALUES (?, ?, ?)", 
                   ("서울특별시", "KR-11", "서울 기지"))
    conn.commit()
    conn.close()
    
    assert get_active_countries() == ["South Korea"]
    
    # 2단계: 미국 지점을 임의로 DB에 등록
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO regions (region_name, region_code, description) VALUES (?, ?, ?)", 
                   ("캘리포니아주", "US-CA", "미국 기지"))
    conn.commit()
    conn.close()
    
    # 동적으로 미국이 감지되어 리스트에 South Korea와 함께 리턴되어야 함
    countries = get_active_countries()
    assert "South Korea" in countries
    assert "United States" in countries
    assert len(countries) == 2

def test_lkv_timestamp_freshness_and_sync():
    """
    LKV에 동기화 완료 후 timestamp가 정상 기록되고 복원되는지 검증
    """
    mock_data = {
        "South Korea": {
            "weather": "Sunny",
            "macro": {"oil_change_pct": 1.2},
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    }
    
    # 저장
    save_lkv(mock_data)
    
    # 로드
    loaded_data = load_lkv()
    
    assert "South Korea" in loaded_data
    assert loaded_data["South Korea"]["weather"] == "Sunny"
    assert loaded_data["South Korea"]["macro"]["oil_change_pct"] == 1.2
    
    # 타임스탬프 형식 검증
    ts_str = loaded_data["South Korea"]["timestamp"]
    parsed_ts = datetime.datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
    assert isinstance(parsed_ts, datetime.datetime)

def test_lkv_atomic_write_safety():
    """
    save_lkv 실행 중 원자적 쓰기가 작동하여, 기존 데이터 파일 손상 없이 안전하게 저장되는지 검증
    """
    # 1. 초기 데이터 저장
    initial_data = {"United States": {"weather": "Rainy"}}
    save_lkv(initial_data)
    
    # 2. .tmp 임시 파일 생성 후 쓰기 및 안전한 rename 확인
    new_data = {"United States": {"weather": "Snowy"}}
    save_lkv(new_data)
    
    loaded = load_lkv()
    assert loaded["United States"]["weather"] == "Snowy"
    
    # 임시 파일이 디스크에 남아있지 않아야 함
    assert not os.path.exists(TEST_LKV_PATH + ".tmp")
