import json, os, sys, pandas as pd, numpy as np, matplotlib.pyplot as plt
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
from matplotlib import rc
import streamlit as st
from utils.macro_connector import GlobalMacroEngine
st.set_page_config(page_title="SCM Agent Dashboard", page_icon="📦", layout="wide", initial_sidebar_state="collapsed")
plt.rcParams["axes.unicode_minus"] = False
for f in ["AppleGothic","NanumGothic","Malgun Gothic"]:
    try: rc("font",family=f); break
    except: continue

SCM_DATA_PATH=os.getenv("SCM_DATA_PATH","outputs/scm_dummy_data.json")
ORDER_HISTORY_PATH=os.getenv("HISTORY_OUTPUT_PATH","outputs/order_history.json")
EMERGENCY_PATH=os.getenv("REPORT_OUTPUT_PATH","outputs/emergency_report.json")
SS={30:"수요5x",60:"조달3주↑",80:"복합위기"}

st.markdown("""<style>
.stApp{background:#202124;color:#e8eaed}
[data-testid="collapsedControl"]{display:none}
.block-container{padding:0.5rem 1rem 0 1rem !important;max-width:100% !important}
div[data-testid="stVerticalBlock"]>div{gap:0.3rem !important}
.hdr{background:#292a2d;border-bottom:1px solid #3c4043;padding:8px 16px 6px;margin:-0.5rem -1rem 0.4rem}
.hdr-t{font-size:15px;font-weight:500;color:#e8eaed}.hdr-s{font-size:11px;color:#9aa0a6;margin-top:1px}
.sec{font-size:10px;font-weight:500;color:#9aa0a6;text-transform:uppercase;letter-spacing:.06em;border-bottom:1px solid #3c4043;padding-bottom:4px;margin:0.5rem 0 0.3rem}
.kg{display:grid;grid-template-columns:repeat(5,1fr);gap:6px;margin-bottom:0.3rem}
.kc{background:#292a2d;border:1px solid #3c4043;border-radius:6px;padding:8px 12px}
.kc:hover{border-color:#8ab4f8}
.kl{font-size:9px;color:#9aa0a6;text-transform:uppercase;letter-spacing:.04em;margin-bottom:3px}
.kv{font-size:22px;font-weight:400;color:#e8eaed;line-height:1.1}
.kv.b{color:#8ab4f8}.kv.g{color:#81c995}.kv.y{color:#fdd663}.kv.r{color:#f28b82}
.ku{font-size:9px;color:#5f6368;margin-top:2px}
.kb{display:inline-block;font-size:8px;border-radius:3px;padding:1px 5px;margin-top:3px;border:1px solid}
.kb.ok{background:#81c99511;color:#81c995;border-color:#81c99533}
.kb.w{background:#f28b8211;color:#f28b82;border-color:#f28b8233}
.cc{background:#292a2d;border:1px solid #3c4043;border-radius:6px;padding:8px 10px 4px;margin-bottom:4px}
.ct{font-size:11px;font-weight:500;color:#e8eaed;margin-bottom:4px;display:flex;align-items:center;gap:6px}
.dt{width:6px;height:6px;border-radius:50%;display:inline-block}
.gt{background:#292a2d;border:1px solid #3c4043;border-radius:6px;overflow:hidden;margin-bottom:4px;width:100%}
.gt table{width:100%;border-collapse:collapse;font-size:11px}
.gt th{background:#303134;color:#9aa0a6;font-weight:500;font-size:9px;text-transform:uppercase;letter-spacing:.04em;padding:5px 8px;text-align:left;border-bottom:1px solid #3c4043}
.gt td{padding:4px 8px;border-bottom:1px solid #3c4043;color:#e8eaed}
.gt tr:last-child td{border-bottom:none}.gt tr:hover td{background:#35363a}
.bd{display:inline-block;font-size:9px;font-weight:500;border-radius:3px;padding:1px 6px;border:1px solid}
.bd.a{background:#81c99511;color:#81c995;border-color:#81c99533}
.bd.x{background:#f28b8211;color:#f28b82;border-color:#f28b8233}
.ep{border-radius:6px;padding:8px 12px;margin-bottom:4px;border-left:3px solid}
.ec{background:#f28b8209;border-color:#f28b82}.ew{background:#fdd66309;border-color:#fdd663}.en{background:#81c99509;border-color:#81c995}
.et{font-size:11px;font-weight:500;margin-bottom:3px}.eb{font-size:10px;color:#9aa0a6;line-height:1.5}
.sg{display:flex;gap:6px;flex-wrap:wrap;margin-top:4px}
.st2{background:#f28b8209;border:1px solid #f28b8222;border-radius:4px;padding:4px 8px;font-size:10px;color:#f28b82}
.st2 .dl{font-size:8px;color:#5f6368;display:block}
.fb{font-size:9px;color:#5f6368;text-align:right;padding-top:4px;border-top:1px solid #3c4043;margin-top:0.3rem}
div[data-testid="metric-container"]{display:none}
div[data-testid="stButton"] button{display:none !important}
</style>""", unsafe_allow_html=True)

@st.cache_data(ttl=1)
def load_scm():
    if not os.path.exists(SCM_DATA_PATH): return None
    try:
        with open(SCM_DATA_PATH,"r",encoding="utf-8") as f: data=json.load(f)
        df=pd.DataFrame(data)
    except: return None
    if "day_index" not in df.columns and "day" in df.columns: df["day_index"]=df["day"]-1
    if "daily_sales" not in df.columns and "daily_demand" in df.columns: df["daily_sales"]=df["daily_demand"]
    if "incoming_stock" not in df.columns: df["incoming_stock"]=0
    if "stock_level" not in df.columns:
        ords=load_orders(); aq={}
        for o in ords:
            if o.get("status")=="APPROVED":
                od=o["day"]
                if od<=len(df):
                    tr=df[df["day"]==od]
                    if not tr.empty: ad=od+int(round(tr["lead_time_days"].values[0])); aq[ad]=aq.get(ad,0)+o["order_qty"]
        sl,cs=[],1500.0
        for _,r in df.iterrows():
            cs+=aq.get(int(r.get("day",0)),0.0); cs=max(0,cs-r.get("daily_demand",0)); sl.append(cs)
        df["stock_level"]=sl
    if "reorder_point" not in df.columns: df["reorder_point"]=df["daily_sales"].rolling(7,min_periods=1).mean()*7
    if "safety_stock" not in df.columns: df["safety_stock"]=df["daily_sales"].rolling(7,min_periods=1).std().fillna(10)*1.65
    return df

@st.cache_data(ttl=1)
def load_orders():
    if not os.path.exists(ORDER_HISTORY_PATH): return []
    try:
        with open(ORDER_HISTORY_PATH,"r",encoding="utf-8") as f: return json.load(f)
    except: return []

@st.cache_data(ttl=1)
def load_emg(d=0):
    tp=os.path.join("outputs",f"emergency_report_day{d:03d}.json")
    for p in [tp,EMERGENCY_PATH]:
        if os.path.exists(p):
            try:
                with open(p,"r",encoding="utf-8") as f: return json.load(f)
            except: pass
    return None

BG="#292a2d";GR="#3c4043";TX="#9aa0a6"
CL={"s":"#8ab4f8","r":"#f28b82","ss":"#c58af9","d":"#81c995","o":"#fdd663","x":"#f28b82"}

def sax(ax):
    ax.set_facecolor(BG);ax.tick_params(colors=TX,labelsize=7)
    ax.xaxis.label.set_color(TX);ax.yaxis.label.set_color(TX)
    for sp in ax.spines.values():sp.set_edgecolor(GR)
    ax.grid(True,color=GR,lw=0.5,ls="--",alpha=0.7)

def mst(ax,df):
    yl=ax.get_ylim()[1]
    for d,l in SS.items():
        if d<=len(df): ax.axvline(x=d,color=CL["x"],ls="--",alpha=0.4,lw=0.8);ax.text(d+.3,yl*.93,l,fontsize=6,color=CL["x"],rotation=90,va="top",alpha=0.7)

def mk(h=2.0):
    f,ax=plt.subplots(figsize=(13,h),dpi=100);f.patch.set_facecolor(BG);return f,ax

def c_stock(df,orders=None):
    f,ax=mk(2.0);x=df["day_index"]+1
    ax.fill_between(x,df["stock_level"],alpha=.08,color=CL["s"])
    ax.plot(x,df["stock_level"],color=CL["s"],lw=1.4,label="재고")
    ax.plot(x,df["reorder_point"],color=CL["r"],lw=1.0,ls="--",label="ROP")
    ax.plot(x,df["safety_stock"],color=CL["ss"],lw=0.8,ls=":",label="SS")
    if orders:
        ad=[o["day"] for o in orders if o.get("status")=="APPROVED"]
        if ad:
            di=df.set_index(df["day_index"]+1);vd=[d for d in ad if d in di.index]
            if vd: ax.scatter(vd,di.loc[vd,"stock_level"],color=CL["o"],s=20,zorder=5,marker="^")
    sax(ax);mst(ax,df);ax.set_xlabel("Day",fontsize=7);ax.set_ylabel("units",fontsize=7)
    ax.legend(fontsize=6,framealpha=0,loc="upper right",labelcolor=TX);f.tight_layout(pad=0.5);return f

def c_sales(df):
    f,ax=mk(2.0);x=df["day_index"]+1
    ax.bar(x,df["daily_sales"],color=CL["d"],alpha=.5,width=.8,label="수요")
    ax.plot(x,df["daily_sales"].rolling(7,min_periods=1).mean(),color="#f28b82",lw=1.2,label="7d MA")
    sax(ax);mst(ax,df);ax.set_xlabel("Day",fontsize=7);ax.set_ylabel("units",fontsize=7)
    ax.legend(fontsize=6,framealpha=0,loc="upper right",labelcolor=TX);f.tight_layout(pad=0.5);return f

def c_rop(df):
    f,ax=mk(1.8);x=df["day_index"]+1
    ax.fill_between(x,df["safety_stock"],df["reorder_point"],alpha=.07,color=CL["r"])
    ax.plot(x,df["reorder_point"],color=CL["r"],lw=1.4,label="ROP")
    ax.plot(x,df["safety_stock"],color=CL["ss"],lw=1.0,ls="--",label="SS")
    sax(ax);mst(ax,df);ax.set_xlabel("Day",fontsize=7);ax.set_ylabel("units",fontsize=7)
    ax.legend(fontsize=6,framealpha=0,loc="upper right",labelcolor=TX);f.tight_layout(pad=0.5);return f

def c_ord(orders):
    if not orders: return None
    do=pd.DataFrame(orders);f,ax=mk(1.8)
    ap=do[do["status"]=="APPROVED"];bl=do[do["status"]=="BLOCKED"]
    if not ap.empty: ax.bar(ap["day"],ap["order_qty"],color=CL["o"],alpha=.8,width=.8,label="승인")
    if not bl.empty: ax.bar(bl["day"],bl["order_qty"],color=CL["x"],alpha=.6,width=.8,label="차단")
    sax(ax);ax.set_xlabel("Day",fontsize=7);ax.set_ylabel("units",fontsize=7)
    ax.legend(fontsize=6,framealpha=0,loc="upper right",labelcolor=TX);f.tight_layout(pad=0.5);return f

def render_main_dashboard():
    st_autorefresh(interval=1000,key="scm_live")
    df=load_scm();orders=load_orders()
    cd=int(df["day_index"].max()+1) if df is not None and "day_index" in df.columns else 0
    emg=load_emg(cd)

    # ROW 0: Header
    st.markdown(f'<div class="hdr"><div class="hdr-t">📦 SCM 자율 에이전트 100일 압축 시뮬레이션 대시보드</div><div class="hdr-s">Team Sigma | Data→Analysis→Action 관제탑 &nbsp;·&nbsp; Day {cd}/100 &nbsp;·&nbsp; {datetime.now().strftime("%H:%M:%S")} 실시간</div></div>',unsafe_allow_html=True)

    if df is None:
        st.error("❌ 데이터 없음 — `python main.py` 실행 필요");st.stop()

    # ROW 1: KPI
    ms=df["stock_level"].min();av=df["daily_sales"].mean()
    to=sum(1 for o in orders if o.get("status")=="APPROVED");bc=sum(1 for o in orders if o.get("status")=="BLOCKED");sok=ms>0
    st.markdown(f'''<div class="kg">
<div class="kc"><div class="kl">타임라인</div><div class="kv b">{cd}/100일</div><div class="ku">진행률 {cd}%</div></div>
<div class="kc"><div class="kl">평균 수요</div><div class="kv">{av:.0f}</div><div class="ku">units/day</div></div>
<div class="kc"><div class="kl">최저 재고</div><div class="kv {"g" if sok else "r"}">{ms:.0f}</div><div class="ku">units</div><div class="kb {"ok" if sok else "w"}">{"● 안전" if sok else "▲ 위험"}</div></div>
<div class="kc"><div class="kl">발주 승인</div><div class="kv y">{to}</div><div class="ku">회 집행</div></div>
<div class="kc"><div class="kl">가드레일</div><div class="kv {"r" if bc>0 else "g"}">{bc}</div><div class="ku">건 차단</div><div class="kb {"w" if bc>0 else "ok"}">{"▲ 차단" if bc>0 else "● 정상"}</div></div>
</div>''',unsafe_allow_html=True)

    # ROW 2: Main charts side-by-side
    r2a,r2b=st.columns(2)
    with r2a:
        st.markdown('<div class="cc"><div class="ct"><span class="dt" style="background:#8ab4f8"></span>재고 변동 · ROP · SS</div>',unsafe_allow_html=True)
        st.pyplot(c_stock(df,orders));st.markdown('</div>',unsafe_allow_html=True)
    with r2b:
        st.markdown('<div class="cc"><div class="ct"><span class="dt" style="background:#81c995"></span>일일 수요량 추이</div>',unsafe_allow_html=True)
        st.pyplot(c_sales(df));st.markdown('</div>',unsafe_allow_html=True)

    # ROW 3: Left=ROP+발주 차트 세로 스택 / Right=이력 테이블+비상 보고서
    r3L,r3R=st.columns([1.2,1])
    with r3L:
        st.markdown('<div class="cc"><div class="ct"><span class="dt" style="background:#f28b82"></span>동적 발주점 (ROP) 변화 추이</div>',unsafe_allow_html=True)
        st.pyplot(c_rop(df));st.markdown('</div>',unsafe_allow_html=True)
        fo=c_ord(orders)
        if fo:
            st.markdown('<div class="cc"><div class="ct"><span class="dt" style="background:#fdd663"></span>발주 타임라인 (승인 / 차단)</div>',unsafe_allow_html=True)
            st.pyplot(fo);st.markdown('</div>',unsafe_allow_html=True)
    with r3R:
        st.markdown('<div class="sec">📋 전체 발주 제어 상세 이력부</div>',unsafe_allow_html=True)
        if orders:
            df_orders = pd.DataFrame(orders)
            if not df_orders.empty and "order_id" in df_orders.columns:
                df_orders = df_orders.drop_duplicates(subset=["order_id"], keep="last")
                df_orders = df_orders.sort_values(by="day", ascending=False)
                order_list = df_orders.head(50).to_dict(orient="records")
                rows = "".join([
                    f'<tr>'
                    f'<td style="color:#8ab4f8;font-family:monospace;font-size:10px">{o.get("order_id","—")}</td>'
                    f'<td>{o.get("day","—")}일차</td>'
                    f'<td>{o.get("order_qty",0):,.0f}</td>'
                    f'<td><span class="bd {"a" if o.get("status")=="APPROVED" else "x"}">{o.get("status","—")}</span></td>'
                    f'<td style="color:#9aa0a6;font-size:9px">{o.get("note","—")}</td>'
                    f'</tr>'
                    for o in order_list
                ])
                st.markdown(f'''<div class="gt" style="max-height:280px;overflow-y:auto;">
                    <table><thead><tr><th>발주 ID</th><th>일차</th><th>수량</th><th>상태</th><th>비고</th></tr></thead>
                    <tbody>{rows}</tbody></table></div>''',unsafe_allow_html=True)
        else:
            st.markdown('<div class="ep en"><div class="et">발주 이력 없음</div></div>',unsafe_allow_html=True)
        st.markdown('<div class="sec">🚨 비상 보고서</div>',unsafe_allow_html=True)
        if emg:
            lv=emg.get("alert_level","NORMAL")
            cl="ec" if lv=="CRITICAL" else "ew" if lv=="WARNING" else "en"
            ic="🔴" if lv=="CRITICAL" else "🟡" if lv=="WARNING" else "🟢"
            st.markdown(f'<div class="ep {cl}"><div class="et">{ic} [{lv}] Day{cd}</div><div class="eb">{emg.get("situation_summary","")[:80]}</div></div>',unsafe_allow_html=True)
        else:
            st.markdown('<div class="ep en"><div class="et">🟢 정상</div><div class="eb">비상 신호 없음</div></div>',unsafe_allow_html=True)
        st.markdown('<div class="sec">⚡ 스트레스</div>',unsafe_allow_html=True)
        st.markdown('<div class="sg">'+"".join([f'<div class="st2"><span class="dl">D{d}</span>{l}</div>' for d,l in SS.items()])+'</div>',unsafe_allow_html=True)

    st.markdown(f'<div class="fb">🔄 {datetime.now().strftime("%H:%M:%S")} · 1초 자동 스트리밍</div>',unsafe_allow_html=True)


import requests
import yfinance as yf
import ssl
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
            "Spain": [(8221, "Madrid", 40.4168, -3.7048), (8181, "Barcelona", 41.3851, 2.1734)],
            "United States": [(72295, "Los Angeles", 33.9416, -118.4085), (74486, "New York JFK", 40.6397, -73.7789)]
        }
        for country_name, stations in all_regions.items():
            for stn_id, name, lat, lon in stations:
                world_data["country"].append(country_name)
                world_data["station_name"].append(name)
                world_data["station_id"].append(stn_id)
                world_data["latitude"].append(lat)
                world_data["longitude"].append(lon)
        pd.DataFrame(world_data).to_csv(csv_path, index=False)
    return pd.read_csv(csv_path)

def get_live_weather_by_station(station_id, lat=None, lon=None):
    utc_now = datetime.now(datetime.timezone.utc) if hasattr(datetime, 'timezone') else datetime.utcnow()
    target_time = (utc_now - pd.Timedelta(hours=2)).strftime("%Y%m%d%H00")
    kma_key = st.secrets.get("KMA_API_KEY", os.environ.get("KMA_API_KEY", ""))
    url = "https://apihub.kma.go.kr/api/typ01/url/gts_syn1.php"
    
    kma_text = ""
    if kma_key:
        params = {"tm": target_time, "dtm": "3", "stn": int(station_id), "help": "0", "authKey": kma_key}
        try:
            response = requests.get(url, params=params, timeout=7)
            if response.status_code == 200:
                if "AUTH_ERROR" in response.text or "ERROR" in response.text:
                    kma_text = f"⚠️ 기상청 API 에러: {response.text.strip()}"
                else:
                    # 실제 데이터 라인이 있는지 검사 (숫자로 시작하는 줄)
                    has_data = any(line.strip() and line.strip()[0].isdigit() for line in response.text.split('\n'))
                    if has_data:
                        return response.text
        except Exception as e:
            pass

    # KMA 데이터가 없거나 에러가 났을 때 OpenWeatherMap으로 Fallback
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
            except: pass
            
    if kma_text: return kma_text
    return "⚠️ 기상 데이터 지연 및 대체 데이터 수신 실패"

def main():
    st.sidebar.title("SCM 관제 시스템 메뉴")
    menu = st.sidebar.radio("이동", ["메인 대시보드", "글로벌 기상 임베딩"])

    if menu == "메인 대시보드":
        render_main_dashboard()
    elif menu == "글로벌 기상 임베딩":
        st.title("🛰️ SCM 글로벌 관제 제어 센터")
        
        wmo_master_df = load_wmo_master()
        st.sidebar.header("🔍 글로벌 SCM 거점 초고속 검색")
        available_countries = [c for c in sorted(wmo_master_df['country'].dropna().unique()) if c != "Malaysia"]
        
        selected_country = st.sidebar.selectbox("🏳️🌈 1. 대상 국가 선택", options=available_countries, index=available_countries.index("South Korea") if "South Korea" in available_countries else 0)
        filtered_stations = wmo_master_df[wmo_master_df['country'] == selected_country]
        selected_station_name = st.sidebar.selectbox(f"🏙️ 2. {selected_country} 내 허브 거점 선택", options=filtered_stations['station_name'])
        
        matched_station = filtered_stations[filtered_stations['station_name'] == selected_station_name].iloc[0]
        
        st.info(f"🌐 **[SCM 제어 시스템]** 관제 타겟: **{matched_station['station_name']} ({selected_country})** | 위치: `{matched_station['latitude']} / {matched_station['longitude']}`")
        
        st.markdown("---")
        st.markdown(f"### 📊 {selected_country} 중심 공급망 리스크 벡터")
        
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
            
        # 2계층 지표
        st.subheader("🏛️ 2계층: 통화 정책 및 내수 인플레이션 벡터")
        e_col1, e_col2, e_col3 = st.columns(3)
        
        rate_display = f"{data_vector['interest_rate']}%" if data_vector['interest_rate'] is not None else "N/A (미제공)"
        e_col1.metric(label=f"{selected_country} 고유 기준금리", value=rate_display, delta="FRED 고유국가 직접 동기화")
        
        inf_display = f"{data_vector['inflation_rate']:.2f}%" if data_vector['inflation_rate'] is not None else "N/A (미제공)"
        e_col2.metric(label=f"{selected_country} 소비자물가상승률(YoY)", value=inf_display, delta="실질 변동률 정제 완료")
        
        e_col3.metric(label="⚠️ 종합 위험 스코어", value=f"{data_vector['integrated_risk_score']} / 100")
            
        st.markdown("---")
        st.markdown("### 📡 기상청 GTS 실시간 수집 RAW 전문 스트림")
        st.code(get_live_weather_by_station(matched_station['station_id'], matched_station['latitude'], matched_station['longitude']), language="text")

if __name__=="__main__": main()
