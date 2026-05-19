# utils/weather_connector.py
import os
import datetime
import requests
import sqlite3
import numpy as np
import pandas as pd
from typing import Optional, Dict, Union

from db import get_db_connection
from agents.config import PATHS

def get_live_weather_by_station(station_id: Union[int, str], lat: Optional[float] = None, lon: Optional[float] = None) -> str:
    """
    기존 글로벌 공급망 관제탑 및 백그라운드 워커와의 하위 호환성을 위한 함수.
    주어진 WMO station_id 에 대해 기상청 GTS API를 호출하거나 적절한 fallback 날씨 데이터를 반환합니다.
    """
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    target_time = (utc_now - datetime.timedelta(hours=2)).strftime("%Y%m%d%H00")
    
    api_key = os.environ.get("KMA_API_KEY", "")
    url = "https://apihub.kma.go.kr/api/typ01/url/gts_syn1.php"
    params = {
        "tm": target_time,
        "dtm": "3",
        "stn": int(station_id),
        "help": "0",
        "authKey": api_key
    }
    try:
        if not api_key:
            return f"Clear sky. Temperature: 22.5C, Humidity: 45%, Precipitation: 0.0mm (Mock Station {station_id})"
        response = requests.get(url, params=params, timeout=7)
        if response.status_code == 200:
            if "AUTH_ERROR" in response.text or "ERROR" in response.text:
                return f"⚠️ 기상청 API 에러: {response.text.strip()} (Mock Station {station_id})"
            return response.text
        return f"⚠️ 서버 응답 에러 (Status: {response.status_code})"
    except Exception as e:
        return f"🚨 API 연결 실패: {str(e)}"

# ── [3단계] 대한민국 표준 지역별 기상 메타데이터 (위/경도 및 기상청 지점번호) ──
REGION_WEATHER_META = {
    "KR-11": {"name": "서울특별시", "lat": 37.5665, "lon": 126.9780, "station_id": 108},
    "KR-26": {"name": "부산광역시", "lat": 35.1796, "lon": 129.0756, "station_id": 159},
    "KR-27": {"name": "대구광역시", "lat": 35.8714, "lon": 128.6014, "station_id": 143},
    "KR-28": {"name": "인천광역시", "lat": 37.4563, "lon": 126.7052, "station_id": 112},
    "KR-29": {"name": "광주광역시", "lat": 35.1595, "lon": 126.8526, "station_id": 156},
    "KR-30": {"name": "대전광역시", "lat": 36.3504, "lon": 127.3845, "station_id": 133},
    "KR-31": {"name": "울산광역시", "lat": 35.5389, "lon": 129.3114, "station_id": 152},
    "KR-36": {"name": "세종특별자치시", "lat": 36.4801, "lon": 127.2890, "station_id": 239},
    "KR-41": {"name": "경기도", "lat": 37.2636, "lon": 127.0286, "station_id": 119},  # 수원 지점
    "KR-42": {"name": "강원특별자치도", "lat": 37.8854, "lon": 127.7298, "station_id": 101},  # 춘천 지점
    "KR-43": {"name": "충청북도", "lat": 36.6372, "lon": 127.4897, "station_id": 131},  # 청주 지점
    "KR-44": {"name": "충청남도", "lat": 36.6588, "lon": 126.6728, "station_id": 177},  # 홍성 지점
    "KR-45": {"name": "전북특별자치도", "lat": 35.8242, "lon": 127.1480, "station_id": 146},  # 전주 지점
    "KR-46": {"name": "전라남도", "lat": 34.8160, "lon": 126.4629, "station_id": 165},  # 목포 지점
    "KR-47": {"name": "경상북도", "lat": 36.5760, "lon": 128.5056, "station_id": 138},  # 안동 지점
    "KR-48": {"name": "경상남도", "lat": 35.2376, "lon": 128.6924, "station_id": 155},  # 창원 지점
    "KR-49": {"name": "제주특별자치도", "lat": 33.4996, "lon": 126.5312, "station_id": 184}  # 제주 지점
}

def load_wmo_master() -> pd.DataFrame:
    """WMO 마스터 파일 로드"""
    csv_path = PATHS["WMO_CSV"]
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"WMO 마스터 파일이 존재하지 않습니다: {csv_path}")
    return pd.read_csv(csv_path)

def get_seeded_mock_weather(region_code: str, date_str: str) -> Dict:
    """
    API 키가 없거나 호출이 실패했을 때, 결정론적(Seeded)으로 재현 가능한 모의 날씨 데이터를 생성합니다.
    지역 코드와 날짜 문자열의 해시를 시드로 삼아 일관성을 확보합니다.
    """
    # 날짜에서 월 정보 추출하여 계절성 반영
    try:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        month = dt.month
    except Exception:
        month = 5  # 기본값: 5월
        
    # 해시 시드 생성
    seed_val = abs(hash(f"{region_code}_{date_str}")) % (2**32)
    rng = np.random.default_rng(seed_val)
    
    # 월별 평균 기온 설정
    # 1월: -3, 5월: 18, 8월: 26, 10월: 15
    month_temps = {
        1: -3.0, 2: -1.0, 3: 5.0, 4: 12.0, 5: 18.0, 6: 22.0,
        7: 25.0, 8: 27.0, 9: 21.0, 10: 15.0, 11: 7.0, 12: 0.0
    }
    base_temp = month_temps.get(month, 15.0)
    
    # 제주(KR-49)는 상대적으로 온난하게 보정
    if region_code == "KR-49":
        base_temp += 4.0
        
    temp = round(float(rng.normal(loc=base_temp, scale=3.0)), 1)
    humidity = round(float(rng.uniform(low=40.0, high=90.0)), 1)
    
    # 15% 확률로 비 또는 눈 발생
    precip_chance = rng.random()
    if precip_chance < 0.15:
        precipitation = round(float(rng.uniform(low=1.0, high=25.0)), 1)
        if temp <= 0.0:
            weather_desc = "Snow"
        else:
            weather_desc = "Rain"
            # 비가 오면 습도를 높게 보정
            humidity = min(100.0, humidity + 15.0)
    else:
        precipitation = 0.0
        weather_desc = rng.choice(["Clear", "Clouds", "Partly Cloudy"])
        
    return {
        "temp": temp,
        "humidity": humidity,
        "precipitation": precipitation,
        "weather_desc": weather_desc
    }

def fetch_live_weather(region_code: str, date_str: str) -> Dict:
    """
    외부 OpenWeatherMap API 또는 기상청 API를 통해 실시간 데이터를 수집합니다.
    API 호출에 실패하거나 키가 없을 경우 결정론적 모의 데이터로 대체합니다.
    """
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    if date_str != today_str:
        # 과거 날짜는 실시간 API 대상이 아니므로 결정론적 모의 데이터를 반환하여 일자별 변동성을 확보합니다.
        return get_seeded_mock_weather(region_code, date_str)

    meta = REGION_WEATHER_META.get(region_code)
    if not meta:
        return get_seeded_mock_weather(region_code, date_str)
        
    ow_key = os.environ.get("OPENWEATHER_API_KEY", "")
    
    # 1. OpenWeatherMap API 호출 시도
    if ow_key:
        lat, lon = meta["lat"], meta["lon"]
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={ow_key}&units=metric"
        try:
            res = requests.get(url, timeout=3.0)
            if res.status_code == 200:
                data = res.json()
                temp = float(data.get("main", {}).get("temp", 15.0))
                humidity = float(data.get("main", {}).get("humidity", 60.0))
                
                # 강수량 추출
                precipitation = 0.0
                if "rain" in data and "1h" in data["rain"]:
                    precipitation = float(data["rain"]["1h"])
                elif "snow" in data and "1h" in data["snow"]:
                    precipitation = float(data["snow"]["1h"])
                    
                weather_desc = data.get("weather", [{}])[0].get("main", "Clear")
                
                return {
                    "temp": round(temp, 1),
                    "humidity": round(humidity, 1),
                    "precipitation": round(precipitation, 1),
                    "weather_desc": weather_desc
                }
        except Exception:
            pass # 실패 시 KMA 또는 Mock Fallback 진행
            
    # 2. 기상청 API 호출 시도 (참고용 구조 제공, 실제 서비스 키 없을 시 Mock)
    # 기상청 연동을 원할 시 KMA_API_KEY 설정이 필요하며, 여기서는 모의 데이터로 최종 Fallback합니다.
    return get_seeded_mock_weather(region_code, date_str)

def get_weather_for_region(region_code: str, date_str: str) -> Dict:
    """
    지역별, 날짜별 날씨 정보를 가져옵니다. (로컬 캐싱 적용)
    - 과거 날짜 데이터: 무조건 캐시 영구 사용.
    - 오늘 날짜 데이터: 캐시가 존재하고 1시간 이내에 갱신되었으면 캐시 사용, 그렇지 않으면 외부 호출 후 캐시 갱신.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. DB 캐시 확인
    cursor.execute("""
        SELECT temp, humidity, precipitation, weather_desc, updated_at
        FROM weather_cache
        WHERE region_code = ? AND date = ?
    """, (region_code, date_str))
    row = cursor.fetchone()
    
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    is_fresh = False
    
    if row:
        if date_str != today_str:
            # 과거 데이터는 캐시가 영구적으로 신선함
            is_fresh = True
        else:
            # 오늘 데이터는 1시간 이내인지 검증
            updated_at_str = row["updated_at"]
            try:
                # ISO 포맷 등 날짜 파싱
                updated_at = datetime.datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
            except Exception:
                try:
                    updated_at = datetime.datetime.strptime(updated_at_str, "%Y-%m-%d %H:%M:%S")
                except Exception:
                    updated_at = None
                    
            if updated_at:
                diff = datetime.datetime.now() - updated_at
                if diff.total_seconds() < 3600: # 1시간 미만
                    is_fresh = True
                    
    # 2. 캐시가 존재하고 신선하면 캐시 값 반환
    if is_fresh and row:
        conn.close()
        return {
            "temp": row["temp"],
            "humidity": row["humidity"],
            "precipitation": row["precipitation"],
            "weather_desc": row["weather_desc"]
        }
        
    # 3. 신선하지 않거나 캐시가 없으면 외부 API 호출
    weather_data = fetch_live_weather(region_code, date_str)
    
    # 4. DB 캐시 갱신 (UPSERT)
    try:
        cursor.execute("""
            INSERT INTO weather_cache (region_code, date, temp, humidity, precipitation, weather_desc, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(region_code, date) DO UPDATE SET
                temp = excluded.temp,
                humidity = excluded.humidity,
                precipitation = excluded.precipitation,
                weather_desc = excluded.weather_desc,
                updated_at = CURRENT_TIMESTAMP
        """, (
            region_code,
            date_str,
            weather_data["temp"],
            weather_data["humidity"],
            weather_data["precipitation"],
            weather_data["weather_desc"]
        ))
        conn.commit()
    except Exception as e:
        conn.rollback()
        # 로깅 후 무시하고 결과는 반환
        print(f"⚠️ 날씨 캐시 갱신 실패 (무시됨): {e}")
    finally:
        conn.close()
        
    return weather_data
