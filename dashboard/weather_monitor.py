import os
import datetime
import pandas as pd
import requests
import streamlit as st
from utils.macro_connector import GlobalMacroEngine

@st.cache_data
def load_wmo_master():
    csv_path = "data/wmo_station_master.csv"
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(csv_path) or os.path.getsize(csv_path) < 1000:
        world_data = {"country": [], "station_name": [], "station_id": [], "latitude": [], "longitude": []}
        all_regions = {
            "South Korea": [(152, "Ulsan", 35.5389, 129.3114), (159, "Busan", 35.1017, 129.0300), (108, "Seoul", 37.5665, 126.9780)],
            "Japan": [(47662, "Tokyo", 35.6895, 139.6917), (47740, "Osaka", 34.6937, 135.5023), (47807, "Fukuoka", 33.5904, 130.4017)],
            "China": [(58362, "Shanghai", 31.4000, 121.4667), (54511, "Beijing", 39.9042, 116.4074)],
            "Singapore": [(48698, "Singapore Changi", 1.3521, 103.9940)],
            "Australia": [(94768, "Sydney", -33.8688, 151.2093), (94608, "Adelaide", -34.9285, 138.6007)],
            "Taiwan": [(58968, "Taipei", 25.0330, 121.5654)],
            "Germany": [(10382, "Berlin", 52.5200, 13.4050), (10637, "Frankfurt", 50.1109, 8.6821)],
            "Spain": [(8221, "Madrid", 40.4168, -3.7038), (8181, "Barcelona", 41.3851, 2.1734)],
            "United States": [(72295, "Los Angeles", 33.9416, -118.4085), (74486, "New York JFK", 40.6397, -73.7789)]
        }
        for country_name, stations in all_regions.items():
            for stn_id, name, lat, lon in stations:
                world_data["country"].append(country_name)
                world_data["station_name"].append(name)
                world_data["station_id"].append(stn_id)
                world_data["latitude"].append(lat)
                world_data["longitude"].append(lon)
        df = pd.DataFrame(world_data)
        df.to_csv(csv_path, index=False)
    return pd.read_csv(csv_path)

def get_live_weather_by_station(station_id):
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    target_time = (utc_now - datetime.timedelta(hours=2)).strftime("%Y%m%d%H00")
    url = "https://apihub.kma.go.kr/api/typ01/url/gts_syn1.php"
    params = {"tm": target_time, "dtm": "3", "stn": int(station_id), "help": "0", "authKey": "JpFeXXhKSciRXl14SjnIkg"}
    try:
        response = requests.get(url, params=params, timeout=7)
        return response.text if response.status_code == 200 else "⚠️ 기상 데이터 지연"
    except:
        return "🚨 기상 스트림 통신 오류"

def render_weather_dashboard():
    wmo_master_df = load_wmo_master()
    st.sidebar.header("🔍 글로벌 SCM 거점 초고속 검색")
    available_countries = sorted(wmo_master_df['country'].unique())
    
    selected_country = st.sidebar.selectbox("🏳️🌈 1. 대상 국가 선택", options=available_countries)
    filtered_stations = wmo_master_df[wmo_master_df['country'] == selected_country]
    selected_station_name = st.sidebar.selectbox(f"🏙️ 2. {selected_country} 내 허브 거점 선택", options=filtered_stations['station_name'])
    
    matched_station = filtered_stations[filtered_stations['station_name'] == selected_station_name].iloc[0]
    
    st.info(f"🌐 **[SCM 글로벌 제어 센터]** 관제 타겟: **{matched_station['station_name']} ({selected_country})**")
    
    st.markdown("---")
    st.markdown(f"### 📊 {selected_country} 중심 규격화된 공급망 리스크 벡터")
    
    with st.spinner("글로벌 거시 지표 동기화 중..."):
        macro_engine = GlobalMacroEngine()
        data_vector = macro_engine.fetch_unified_macro_vector(selected_country)
        
        # 1계층 지표
        st.subheader("⚙️ 1계층: 실물 경기 및 금융 변동성 벡터")
        m_col1, m_col2, m_col3 = st.columns(3)
        
        fx_label = f"대미 환율 ({data_vector['currency_code']}/USD)" if data_vector['fx_ticker'] else "기준 통화 (USD)"
        m_col1.metric(label=fx_label, value=f"{data_vector['fx_value']}", delta=f"{data_vector['fx_change_pct']}%")
        
        idx_label = f"시장 지수 ({data_vector['index_ticker']})" if data_vector['index_ticker'] else "시장 지수"
        idx_val = f"{data_vector['index_value']} pt" if data_vector['index_value'] > 0 else "데이터 준비 중"
        m_col2.metric(label=idx_label, value=idx_val, delta=f"{data_vector['index_change_pct']}%")
        m_col3.metric(label="WTI 국제 유가", value=f"${data_vector['oil_price']}", delta=f"{data_vector['oil_change_pct']}%", delta_color="inverse")
            
        # 2계층 지표 (None 방어막 구축)
        st.subheader("🏛️ 2계층: 통화 정책 및 내수 인플레이션 벡터")
        e_col1, e_col2, e_col3 = st.columns(3)
        
        rate_display = f"{data_vector['interest_rate']}%" if data_vector['interest_rate'] is not None else "N/A (미제공)"
        e_col1.metric(label=f"{selected_country} 권역 기준금리", value=rate_display, delta="FRED 고유국가 매핑")
        
        inf_display = f"{data_vector['inflation_rate']:.2f}%" if data_vector['inflation_rate'] is not None else "N/A (미제공)"
        e_col2.metric(label=f"{selected_country} 소비자물가상승률(YoY)", value=inf_display, delta="지수 변환 완료")
        
        e_col3.metric(label="⚠️ 종합 위험 스코어", value=f"{data_vector['integrated_risk_score']} / 100")
            
    st.code(get_live_weather_by_station(matched_station['station_id']), language="text")
