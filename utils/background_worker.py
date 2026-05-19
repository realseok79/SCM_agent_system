import time
import datetime
from utils.state_manager import load_lkv, save_lkv
from utils.weather_connector import get_live_weather_by_station
from utils.macro_connector import GlobalMacroEngine
from agents.data_agent import GlobalIssueTracker, DataAgent
import pandas as pd
from db import get_db_connection

def get_active_countries():
    """
    DB(regions 테이블)에 등록된 지역 코드 정보를 기준으로 활성화된 국가 목록을 동적으로 반환합니다.
    - 예: KR-11 -> South Korea
    - 등록된 국가가 없는 경우 최소 South Korea 1개를 보장합니다.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT region_code FROM regions")
        codes = [row["region_code"] for row in cursor.fetchall()]
        conn.close()
    except Exception as e:
        print(f"⚠️ [Background Worker] DB 조회 실패 (South Korea 기본값 사용): {e}")
        return ["South Korea"]

    # ISO 3166-2 주(Province/State) 코드 또는 지명 매핑
    countries = set()
    for code in codes:
        code_upper = str(code).upper()
        if code_upper.startswith("KR-"):
            countries.add("South Korea")
        elif code_upper.startswith("US-"):
            countries.add("United States")
        elif code_upper.startswith("CN-"):
            countries.add("China")
        elif code_upper.startswith("JP-"):
            countries.add("Japan")
        elif code_upper.startswith("GB-"):
            countries.add("United Kingdom")
        # 추가적인 국가 코드가 들어오는 경우 매핑 확장 가능

    return list(countries) if countries else ["South Korea"]


def run_worker():
    print("🚀 [Background Worker] 가동 시작...")
    macro_engine = GlobalMacroEngine()
    issue_tracker = GlobalIssueTracker()
    
    # DataAgent 초기화 (Trends 수집용)
    try:
        data_agent = DataAgent()
    except Exception as e:
        print(f"⚠️ [DataAgent 초기화 실패]: {e}")
        data_agent = None

    # 기상 관측소 매핑 (간소화)
    station_map = {
        "South Korea": {"id": "47159", "name": "Busan", "lat": 35.1017, "lon": 129.03},
        "United States": {"id": "72503", "name": "New York", "lat": 40.7128, "lon": -74.0060},
        "China": {"id": "54511", "name": "Beijing", "lat": 39.9042, "lon": 116.4074},
        "Japan": {"id": "47662", "name": "Tokyo", "lat": 35.6895, "lon": 139.6917},
        "United Kingdom": {"id": "03772", "name": "London", "lat": 51.5074, "lon": -0.1278},
    }

    while True:
        print(f"\n🕒 [{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 데이터 수집 사이클 시작...")
        state = load_lkv()
        
        for country in get_active_countries():
            print(f"Fetching data for {country}...")
            country_data = state.get(country, {})
            
            # 1. 날씨 수집
            if country in station_map:
                s_info = station_map[country]
                try:
                    weather = get_live_weather_by_station(s_info["id"], s_info["lat"], s_info["lon"])
                    if weather:
                        country_data["weather"] = weather
                except Exception as e:
                    print(f"  ❌ Weather failed for {country}: {e}")
            
            # 2. 매크로 데이터 수집
            try:
                macro_vector = macro_engine.fetch_unified_macro_vector(country)
                if macro_vector:
                    country_data["macro"] = macro_vector
            except Exception as e:
                print(f"  ❌ Macro failed for {country}: {e}")
                
            # 3. GDELT 수집
            try:
                gdelt_info = issue_tracker.fetch_supply_chain_risk_tone(target_country=country)
                if gdelt_info:
                    country_data["gdelt"] = gdelt_info
            except Exception as e:
                print(f"  ❌ GDELT failed for {country}: {e}")
                
            # 4. Google Trends 수집
            if data_agent:
                try:
                    # DataAgent의 _fetch_trend_signal은 내부적으로 키워드를 검색함
                    trends_info = data_agent._fetch_trend_signal()
                    if trends_info:
                        country_data["trends"] = trends_info
                except Exception as e:
                    print(f"  ❌ Trends failed for {country}: {e}")
            
            # 타임스탬프 갱신
            country_data["timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            state[country] = country_data
            
            # 과도한 API 요청 방지를 위한 딜레이
            time.sleep(1)
            
        # 상태 저장
        save_lkv(state)
        print(f"💾 수집 완료 및 저장됨. 30분 대기...")
        time.sleep(1800)  # 30분 주기 (1800초)

if __name__ == "__main__":
    run_worker()
