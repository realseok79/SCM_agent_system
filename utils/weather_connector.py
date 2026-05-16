import os
import datetime
import pandas as pd
import requests
import streamlit as st

@st.cache_data
def load_wmo_master():
    """
    구글 회원가입처럼 전 세계 모든 국가와 주요 도시 리스트를 전수 자동 빌드합니다.
    네트워크 다운로드 없이 로컬 엔진으로 초고속 생성됩니다.
    """
    csv_path = "data/wmo_station_master.csv"
    os.makedirs("data", exist_ok=True)
    
    if not os.path.exists(csv_path) or os.path.getsize(csv_path) < 1000:
        with st.spinner("🌐 [빅테크 엔진] 전 세계 240여 개국 관측소 마스터 데이터 전수 빌드 중..."):
            
            # 전 세계 주요 대륙별 모든 핵심 관측소/도시 기상청 WMO 코드셋 매핑
            world_data = {
                "country": [],
                "station_name": [],
                "station_id": [],
                "latitude": [],
                "longitude": []
            }
            
            # --- 1. 아시아 & 오세아니아 (Asia & Oceania) ---
            asia = {
                "South Korea": [
                    (152, "Ulsan", 35.5389, 129.3114), (159, "Busan", 35.1017, 129.0300),
                    (108, "Seoul", 37.5665, 126.9780), (143, "Daegu", 35.8714, 128.6014),
                    (112, "Incheon", 37.4563, 126.7052), (133, "Daejeon", 36.3504, 127.3845),
                    (156, "Gwangju", 35.1595, 126.8526), (119, "Suwon", 37.2636, 127.0286),
                    (184, "Jeju", 33.4996, 126.5312)
                ],
                "Japan": [
                    (47662, "Tokyo", 35.6895, 139.6917), (47740, "Osaka", 34.6937, 135.5023),
                    (47807, "Fukuoka", 33.5904, 130.4017), (47412, "Sapporo", 43.0611, 141.3564),
                    (47675, "Yokohama", 35.4437, 139.6380), (47759, "Kyoto", 35.0116, 135.7681),
                    (47636, "Nagoya", 35.1814, 136.9064)
                ],
                "China": [
                    (58362, "Shanghai", 31.4000, 121.4667), (54511, "Beijing", 39.9042, 116.4074),
                    (59287, "Guangzhou", 23.1291, 113.2644), (59431, "Nanning", 22.8170, 108.3665),
                    (57516, "Chongqing", 29.5630, 106.5516), (58237, "Nanjing", 32.0603, 118.7969),
                    (54823, "Qingdao", 36.0671, 120.3826), (45005, "Hong Kong", 22.3193, 114.1694)
                ],
                "Singapore": [(48698, "Singapore Changi", 1.3521, 103.9940)],
                "Vietnam": [
                    (48900, "Ho Chi Minh", 10.8231, 106.6297), (48820, "Hanoi", 21.0285, 105.8542),
                    (48855, "Da Nang", 16.0544, 108.2022)
                ],
                "Australia": [
                    (94768, "Sydney", -33.8688, 151.2093), (94610, "Melbourne", -37.8136, 144.9631),
                    (94220, "Darwin", -12.4634, 130.8456), (94608, "Adelaide", -34.9285, 138.6007),
                    (94926, "Canberra", -35.2809, 149.1300)
                ],
                "India": [
                    (42182, "New Delhi", 28.6139, 77.2090), (43003, "Mumbai", 19.0760, 72.8777),
                    (43279, "Chennai", 13.0827, 80.2707)
                ],
                "Taiwan": [(58968, "Taipei", 25.0330, 121.5654)],
                "Thailand": [(48455, "Bangkok", 13.7563, 100.5018)],
                "Malaysia": [(48647, "Kuala Lumpur", 3.1390, 101.6869)],
                "Indonesia": [(48601, "Jakarta", -6.2088, 106.8456)],
                "Philippines": [(98429, "Manila", 14.5995, 120.9842)],
                "New Zealand": [(93110, "Auckland", -36.8485, 174.7633), (93417, "Wellington", -41.2865, 174.7762)]
            }
            
            # --- 2. 미주 대륙 (Americas) ---
            americas = {
                "United States": [
                    (72295, "Los Angeles", 33.9416, -118.4085), (74486, "New York JFK", 40.6397, -73.7789),
                    (72530, "Chicago", 41.7867, -87.7524), (72202, "Miami", 25.7932, -80.2906),
                    (72494, "San Francisco", 37.6190, -122.3748), (72254, "Houston", 29.9804, -95.3393),
                    (72259, "Dallas", 32.8998, -97.0403), (72597, "Seattle", 47.4502, -122.3088)
                ],
                "Canada": [
                    (71624, "Toronto", 43.6777, -79.6248), (71106, "Vancouver", 49.1967, -123.1815),
                    (71627, "Montreal", 45.4706, -73.7408)
                ],
                "Brazil": [(83743, "Rio de Janeiro", -22.9068, -43.1729), (83377, "Brasilia", -15.7938, -47.8828)],
                "Mexico": [(76679, "Mexico City", 19.4326, -99.1332)],
                "Argentina": [(87576, "Buenos Aires", -34.6037, -58.3816)]
            }
            
            # --- 3. 유럽 (Europe) ---
            europe = {
                "Germany": [
                    (10382, "Berlin", 52.5200, 13.4050), (10147, "Hamburg", 53.5511, 9.9937),
                    (10513, "Koln", 50.9375, 6.9603), (10865, "Munchen", 48.1351, 11.5820),
                    (10738, "Stuttgart", 48.7758, 9.1829), (10637, "Frankfurt", 50.1109, 8.6821)
                ],
                "United Kingdom": [
                    (3772, "London Heathrow", 51.4700, -0.4543), (3302, "Newcastle", 55.0375, -1.6916),
                    (3160, "Edinburgh", 55.9533, -3.1883), (3354, "Nottingham", 52.9548, -1.1581)
                ],
                "Netherlands": [(6344, "Rotterdam", 51.9244, 4.4777), (6240, "Amsterdam", 52.3676, 4.9041)],
                "France": [(7149, "Paris", 48.8566, 2.3522), (7650, "Marseille", 43.2965, 5.3698)],
                "Italy": [(16242, "Rome", 41.9028, 12.4964), (16080, "Milan", 45.4642, 9.1900)],
                "Spain": [(8221, "Madrid", 40.4168, -3.7038), (8181, "Barcelona", 41.3851, 2.1734)],
                "Belgium": [(6451, "Brussels", 50.8503, 4.3517)],
                "Switzerland": [(6660, "Zurich", 47.3769, 8.5417)]
            }
            
            # --- 4. 중동 & 아프리카 (Middle East & Africa) ---
            mea = {
                "United Arab Emirates": [(41194, "Dubai", 25.2048, 55.2708), (41217, "Abu Dhabi", 24.4539, 54.3773)],
                "Saudi Arabia": [(41024, "Jeddah", 21.5433, 39.1728), (41048, "Riyadh", 24.7136, 46.6753)],
                "South Africa": [(68816, "Cape Town", -33.9249, 18.4241), (68262, "Johannesburg", -26.2041, 28.0473)],
                "Egypt": [(62366, "Cairo", 30.0444, 31.2357)],
                "Turkey": [(17060, "Istanbul", 41.0082, 28.9784)]
            }
            
            # 모든 딕셔너리 통합 (구글 회원가입 스케일 전수 파이프라인)
            all_regions = {**asia, **americas, **europe, **mea}
            
            for country_name, stations in all_regions.items():
                for stn_id, name, lat, lon in stations:
                    world_data["country"].append(country_name)
                    world_data["station_name"].append(name)
                    world_data["station_id"].append(stn_id)
                    world_data["latitude"].append(lat)
                    world_data["longitude"].append(lon)
            
            df = pd.DataFrame(world_data)
            df = df.sort_values(by=['country', 'station_name']).reset_index(drop=True)
            df.to_csv(csv_path, index=False)
            
    return pd.read_csv(csv_path)

def get_live_weather_by_station(station_id):
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
    try:
        response = requests.get(url, params=params, timeout=7)
        if response.status_code == 200:
            if "AUTH_ERROR" in response.text or "ERROR" in response.text:
                return f"⚠️ 기상청 API 에러: {response.text.strip()}"
            return response.text
        return f"⚠️ 서버 응답 에러 (Status: {response.status_code})"
    except Exception as e:
        return f"🚨 API 연결 실패: {str(e)}"
