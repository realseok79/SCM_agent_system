import os
import datetime
import pandas as pd
import requests
import streamlit as st
from agents.config import PATHS

@st.cache_data
def load_wmo_master() -> pd.DataFrame:
    """
    data/wmo_station_master.csv 순수 로드 (생성 로직 제거)
    """
    csv_path = PATHS["WMO_CSV"]
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"WMO 마스터 파일이 존재하지 않습니다: {csv_path}")
    return pd.read_csv(csv_path)

def get_live_weather_by_station(station_id, lat=None, lon=None):
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    target_time = (utc_now - datetime.timedelta(hours=2)).strftime("%Y%m%d%H00")
    
    api_key = st.secrets.get("KMA_API_KEY", os.environ.get("KMA_API_KEY", ""))
    url = "https://apihub.kma.go.kr/api/typ01/url/gts_syn1.php"
    params = {
        "tm": target_time,
        "dtm": "3",
        "stn": int(station_id),
        "help": "0",
        "authKey": api_key
    }
    kma_text = ""
    if api_key:
        try:
            response = requests.get(url, params=params, timeout=7)
            if response.status_code == 200:
                if "AUTH_ERROR" in response.text or "ERROR" in response.text:
                    kma_text = f"⚠️ 기상청 API 에러: {response.text.strip()}"
                else:
                    has_data = any(line.strip() and line.strip()[0].isdigit() for line in response.text.split('\n'))
                    if has_data:
                        return response.text
        except Exception as e:
            kma_text = f"🚨 API 연결 실패: {str(e)}"

    # fall back to OpenWeatherMap if lat and lon are provided
    if lat is not None and lon is not None:
        ow_key = st.secrets.get("OPENWEATHER_API_KEY", os.environ.get("OPENWEATHER_API_KEY", ""))
        if ow_key:
            ow_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={ow_key}&units=metric"
            try:
                res = requests.get(ow_url, timeout=7)
                if res.status_code == 200:
                    data = res.json()
                    desc = data.get("weather", [{}])[0].get("description", "Unknown")
                    temp = data.get("main", {}).get("temp", "N/A")
                    humidity = data.get("main", {}).get("humidity", "N/A")
                    wind = data.get("wind", {}).get("speed", "N/A")
                    return f"[OpenWeatherMap 대체 데이터 (KMA 미수신/지연)]\n상태: {desc}\n온도: {temp}°C\n습도: {humidity}%\n풍속: {wind}m/s"
            except:
                pass

    if kma_text:
        return kma_text
    return "⚠️ 기상 데이터 지연 및 대체 데이터 수신 실패"
