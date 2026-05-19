import json, os, sys, pandas as pd, numpy as np, matplotlib.pyplot as plt, concurrent.futures, time
import shutil
import tempfile
import sqlite3

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
from matplotlib import rc
import streamlit as st
import importlib

from db import get_db_connection
from models import standardize_region
from utils.data_parser import parse_and_route_file
from utils.weather_connector import get_weather_for_region

import utils.macro_connector
import utils.scoring_engine
importlib.reload(utils.macro_connector)
importlib.reload(utils.scoring_engine)

# 코드 변경이 감지되어 리로드될 때 기존 캐시를 안전하게 1회 비워줍니다.
try:
    st.cache_data.clear()
except Exception:
    pass

from utils.macro_connector import GlobalMacroEngine
from utils.scoring_engine import LogisticsRiskScorer

# 전역 스레드 풀 생성 (Streamlit의 스크립트 재실행 시 블로킹 shutdown을 방지하기 위함)
GLOBAL_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=4)

# 백그라운드 스레드용 수동 캐시 (Streamlit의 st.cache_data가 스레드 내부에서 오작동하는 것을 방지)
MANUAL_CACHE = {}

st.set_page_config(page_title="SCM Agent Dashboard", page_icon="SCM", layout="wide", initial_sidebar_state="expanded")
plt.rcParams["axes.unicode_minus"] = False
for f in ["AppleGothic","NanumGothic","Malgun Gothic"]:
    try: rc("font",family=f); break
    except: continue

from agents.config import PATHS
SCM_DATA_PATH = PATHS["SCM_DATA"]
ORDER_HISTORY_PATH = PATHS["ORDER_HISTORY"]
EMERGENCY_PATH = PATHS["REPORT"]
SS={30:"수요5x",60:"조달3주↑",80:"복합위기"}

st.markdown("""
<style>
/* ── Base ── */
.stApp{background:#202124;color:#e8eaed}
/* Force main content container to stretch full width dynamically, removing empty side gutters */
.block-container, 
[data-testid="stMainBlockContainer"], 
[data-testid="stAppViewBlockContainer"],
.stApp .block-container,
.stApp [data-testid="stMainBlockContainer"],
.stApp [data-testid="stAppViewBlockContainer"] {
    padding: 0 1.5rem 0 1.5rem !important;
    max-width: 98% !important;
    width: 98% !important;
}
div[data-testid="stMain"] {
    padding: 0 !important;
    margin: 0 !important;
}

/* ── Native Sidebar Styling ── */
section[data-testid="stSidebar"] {
    background-color: #202124 !important;
    border-right: 1px solid #3c4043 !important;
}

/* ── Header ── */
.hdr{background:#292a2d;border-bottom:1px solid #3c4043;padding:16px 16px 10px 16px;margin:0 -1.5rem 0.6rem !important;display:flex;align-items:center;gap:14px}
.hdr-t{font-size:15px;font-weight:500;color:#e8eaed}
.hdr-s{font-size:11px;color:#9aa0a6;margin-top:1px}

/* ── Dashboard styles ── */
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
/* stButton style removed to allow custom interactive buttons */
</style>
""", unsafe_allow_html=True)

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

def c_ord(orders, df):
    if not orders: return None
    do=pd.DataFrame(orders);f,ax=mk(1.8)
    ap=do[do["status"]=="APPROVED"];bl=do[do["status"]=="BLOCKED"]
    if not ap.empty: ax.bar(ap["day"],ap["order_qty"],color=CL["o"],alpha=.8,width=.8,label="승인")
    if not bl.empty: ax.bar(bl["day"],bl["order_qty"],color=CL["x"],alpha=.6,width=.8,label="차단")
    sax(ax);ax.set_xlabel("Day",fontsize=7);ax.set_ylabel("units",fontsize=7)
    max_day = int(df["day_index"].max() + 1) if df is not None and "day_index" in df.columns else 100
    ax.set_xlim(1, max_day)
    mst(ax, df)
    ax.legend(fontsize=6,framealpha=0,loc="upper right",labelcolor=TX);f.tight_layout(pad=0.5);return f

def render_main_dashboard():
    st_autorefresh(interval=1000,key="scm_live")
    df=load_scm();orders=load_orders()
    cd=int(df["day_index"].max()+1) if df is not None and "day_index" in df.columns else 0
    emg=load_emg(cd)

    # ROW 0: Header
    st.markdown(f'<div class="hdr"><div><div class="hdr-t">SCM 자율 에이전트 100일 압축 시뮬레이션 대시보드</div><div class="hdr-s">Team Sigma | Data→Analysis→Action 관제탑 &nbsp;·&nbsp; Day {cd}/100 &nbsp;·&nbsp; {datetime.now().strftime("%H:%M:%S")} 실시간</div></div></div>',unsafe_allow_html=True)

    if df is None:
        st.error("데이터 없음 — `python main.py` 실행 필요");st.stop()

    # ROW 1: KPI
    ms=df["stock_level"].min();av=df["daily_sales"].mean()
    to=sum(1 for o in orders if o.get("status")=="APPROVED");bc=sum(1 for o in orders if o.get("status")=="BLOCKED");sok=ms>0
    st.markdown(f'''<div class="kg">
<div class="kc"><div class="kl">타임라인</div><div class="kv b">{cd}/100일</div><div class="ku">진행률 {cd}%</div></div>
<div class="kc"><div class="kl">평균 수요</div><div class="kv">{av:.0f}</div><div class="ku">units/day</div></div>
<div class="kc"><div class="kl">최저 재고</div><div class="kv {"g" if sok else "r"}">{ms:.0f}</div><div class="ku">units</div><div class="kb {"ok" if sok else "w"}">{"안전" if sok else "위험"}</div></div>
<div class="kc"><div class="kl">발주 승인</div><div class="kv y">{to}</div><div class="ku">회 집행</div></div>
<div class="kc"><div class="kl">가드레일</div><div class="kv {"r" if bc>0 else "g"}">{bc}</div><div class="ku">건 차단</div><div class="kb {"w" if bc>0 else "ok"}">{"차단" if bc>0 else "정상"}</div></div>
</div>''',unsafe_allow_html=True)

    # ROW 2: Main charts side-by-side
    r2a,r2b=st.columns(2)
    with r2a:
        st.markdown('<div class="cc"><div class="ct"><span class="dt" style="background:#8ab4f8"></span>재고 변동 · ROP · SS</div>',unsafe_allow_html=True)
        st.pyplot(c_stock(df,orders), use_container_width=True);st.markdown('</div>',unsafe_allow_html=True)
    with r2b:
        st.markdown('<div class="cc"><div class="ct"><span class="dt" style="background:#81c995"></span>일일 수요량 추이</div>',unsafe_allow_html=True)
        st.pyplot(c_sales(df), use_container_width=True);st.markdown('</div>',unsafe_allow_html=True)

    # ROW 3: Left=ROP+발주 차트 세로 스택 / Right=이력 테이블+비상 보고서
    r3L,r3R=st.columns([1.2,1])
    with r3L:
        st.markdown('<div class="cc"><div class="ct"><span class="dt" style="background:#f28b82"></span>동적 발주점 (ROP) 변화 추이</div>',unsafe_allow_html=True)
        st.pyplot(c_rop(df), use_container_width=True);st.markdown('</div>',unsafe_allow_html=True)
        fo=c_ord(orders, df)
        if fo:
            st.markdown('<div class="cc"><div class="ct"><span class="dt" style="background:#fdd663"></span>발주 타임라인 (승인 / 차단)</div>',unsafe_allow_html=True)
            st.pyplot(fo, use_container_width=True);st.markdown('</div>',unsafe_allow_html=True)
    with r3R:
        st.markdown('<div class="sec">전체 발주 제어 상세 이력부</div>',unsafe_allow_html=True)
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
        st.markdown('<div class="sec">비상 보고서</div>',unsafe_allow_html=True)
        if emg:
            lv=emg.get("alert_level","NORMAL")
            cl="ec" if lv=="CRITICAL" else "ew" if lv=="WARNING" else "en"
            ic="[CRITICAL]" if lv=="CRITICAL" else "[WARNING]" if lv=="WARNING" else "[NORMAL]"
            st.markdown(f'<div class="ep {cl}"><div class="et">{ic} Day{cd}</div><div class="eb">{emg.get("situation_summary","")[:80]}</div></div>',unsafe_allow_html=True)
        else:
            st.markdown('<div class="ep en"><div class="et">[정상] 정상</div><div class="eb">비상 신호 없음</div></div>',unsafe_allow_html=True)
        st.markdown('<div class="sec">스트레스</div>',unsafe_allow_html=True)
        st.markdown('<div class="sg">'+"".join([f'<div class="st2"><span class="dl">D{d}</span>{l}</div>' for d,l in SS.items()])+'</div>',unsafe_allow_html=True)

    st.markdown(f'<div class="fb">{datetime.now().strftime("%H:%M:%S")} · 1초 자동 스트리밍</div>',unsafe_allow_html=True)


import requests
import yfinance as yf
import ssl
from utils.weather_connector import load_wmo_master, get_live_weather_by_station
from agents.data_agent import DataAgent
from agents.action_agent import ActionAgent

# 에이전트 인스턴스를 세션 상태에 저장하여 싱글톤 유지
if "data_agent" not in st.session_state:
    st.session_state["data_agent"] = DataAgent()
if "action_agent" not in st.session_state:
    st.session_state["action_agent"] = ActionAgent()

def get_cached_macro_data(country):
    key = f"macro_{country}"
    if key in MANUAL_CACHE and (time.time() - MANUAL_CACHE[key]['time']) < 1800:
        return MANUAL_CACHE[key]['data']
    macro_engine = GlobalMacroEngine()
    data = macro_engine.fetch_unified_macro_vector(country)
    MANUAL_CACHE[key] = {'data': data, 'time': time.time()}
    return data

def get_cached_weather(station_id, lat, lon):
    key = f"weather_{station_id}"
    if key in MANUAL_CACHE and (time.time() - MANUAL_CACHE[key]['time']) < 1800:
        return MANUAL_CACHE[key]['data']
    data = get_live_weather_by_station(station_id, lat, lon)
    MANUAL_CACHE[key] = {'data': data, 'time': time.time()}
    return data

def get_cached_gdelt(country):
    key = f"gdelt_{country}"
    if key in MANUAL_CACHE and (time.time() - MANUAL_CACHE[key]['time']) < 1800:
        return MANUAL_CACHE[key]['data']
    from agents.data_agent import GlobalIssueTracker
    tracker = GlobalIssueTracker()
    data = tracker.fetch_supply_chain_risk_tone(target_country=country)
    MANUAL_CACHE[key] = {'data': data, 'time': time.time()}
    return data

def get_cached_trends(country):
    key = f"trends_{country}"
    if key in MANUAL_CACHE and (time.time() - MANUAL_CACHE[key]['time']) < 1800:
        return MANUAL_CACHE[key]['data']
    from agents.data_agent import DataAgent
    try:
        agent = DataAgent()
        data = agent._fetch_trend_signal()
    except Exception:
        data = {"composite_score": 0.0, "matched_count": 0}
    MANUAL_CACHE[key] = {'data': data, 'time': time.time()}
    return data

def render_simulation_dashboard():
    """
    SIMULATION_MODE: M5 월마트 30,490개 SKU 전체 백테스팅 및 리스크 분석 대시보드
    """
    st.markdown(f'<div class="hdr"><div><div class="hdr-t">M5 백테스팅: 월마트 30,490개 SKU 전체 AI 도입 효과 검증</div><div class="hdr-s">글로벌 공급망 외란 및 기상 이변 하에서 고정 SCM 정책 대비 AI dynamic 최적화 실증분석</div></div></div>', unsafe_allow_html=True)
    
    # 결과 파일 로드
    results_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs", "m5_backtest_results.json"))
    
    if not os.path.exists(results_path):
        st.warning("백테스팅 결과 파일이 존재하지 않습니다. 시뮬레이션을 백그라운드에서 실시간 재생성 중입니다...")
        import subprocess
        subprocess.run(["PYTHONPATH=.", "venv/bin/python", "simulator/m5_backtester.py"], cwd=os.path.dirname(os.path.dirname(results_path)), shell=True)
        
    if not os.path.exists(results_path):
        st.error("백테스팅 엔진 실행 실패. 대시보드를 시뮬레이션 모드로 임시 작동합니다.")
        return
        
    with open(results_path, "r", encoding="utf-8") as f:
        res = json.load(f)
        
    summary = res["summary"]
    top_10 = res["top_10_risk_skus"]
    daily_stats = res["daily_stats"]
    
    # KPI 렌더링
    st.markdown(f'''<div class="kg">
    <div class="kc"><div class="kl">기존 누적 물류비 (Legacy)</div><div class="kv r">₩{summary['total_legacy_cost']:,.0f}</div><div class="ku">고정 ROP / SS / EOQ</div></div>
    <div class="kc"><div class="kl">AI 도입 누적 물류비 (AI SCM)</div><div class="kv g">₩{summary['total_ai_cost']:,.0f}</div><div class="ku">동적 재고 최적화 및 이중 가드레일</div></div>
    <div class="kc"><div class="kl">총 절감 비용 (Savings)</div><div class="kv b">₩{summary['savings']:,.0f}</div><div class="ku">누적 절감액</div></div>
    <div class="kc"><div class="kl">비용 절감률 (Savings %)</div><div class="kv y">{summary['savings_pct']:.1f}%</div><div class="ku">SCM 비용 절감 성과</div></div>
    <div class="kc"><div class="kl">평균 품절율 개선</div><div class="kv b">{summary['average_legacy_stockout_rate']:.2f}% ➔ {summary['average_ai_stockout_rate']:.2f}%</div><div class="ku">품절 위험 대폭 차단</div></div>
    </div>''', unsafe_allow_html=True)
    
    st.markdown("### 공급망 스트레스 테스트 (100일 압축 시뮬레이션 분석)")
    
    # 카테고리 필터링 추가
    categories = ["전체 품목 일괄"] + list(np.unique([k for d in daily_stats for k in d.get("categories", {}).keys()]))
    selected_cat = st.selectbox("품목 카테고리 필터링 (Walmart Category)", options=categories)
    
    days = [d["day"] for d in daily_stats]
    
    legacy_cum = []
    ai_cum = []
    legacy_stockout = []
    ai_stockout = []
    
    curr_leg = 0.0
    curr_ai = 0.0
    
    for d in daily_stats:
        if selected_cat == "전체 품목 일괄":
            leg_cost = d["legacy"]["total_cost"]
            ai_cost = d["ai"]["total_cost"]
            leg_so = d["legacy"]["stockout_rate"]
            ai_so = d["ai"]["stockout_rate"]
        else:
            cat_data = d.get("categories", {}).get(selected_cat, {"legacy": {"total_cost": 0, "stockout_rate": 0}, "ai": {"total_cost": 0, "stockout_rate": 0}})
            leg_cost = cat_data["legacy"]["total_cost"]
            ai_cost = cat_data["ai"]["total_cost"]
            leg_so = cat_data["legacy"]["stockout_rate"]
            ai_so = cat_data["ai"]["stockout_rate"]
            
        curr_leg += leg_cost
        curr_ai += ai_cost
        
        legacy_cum.append(curr_leg)
        ai_cum.append(curr_ai)
        legacy_stockout.append(leg_so)
        ai_stockout.append(ai_so)
        
    df_cost = pd.DataFrame({
        "Day": days,
        "기존 SCM 누적 비용 (Legacy)": legacy_cum,
        "AI Dynamic SCM 누적 비용": ai_cum
    }).set_index("Day")
    
    df_stockout = pd.DataFrame({
        "Day": days,
        "기존 SCM 평균 품절율 (%)": legacy_stockout,
        "AI Dynamic SCM 평균 품절율 (%)": ai_stockout
    }).set_index("Day")
    
    r1, r2 = st.columns(2)
    with r1:
        st.markdown('<div class="cc"><div class="ct"><span class="dt" style="background:#8ab4f8"></span>누적 물류 총비용 추이 (Holding + Stockout)</div>', unsafe_allow_html=True)
        st.line_chart(df_cost)
        st.markdown('</div>', unsafe_allow_html=True)
    with r2:
        st.markdown('<div class="cc"><div class="ct"><span class="dt" style="background:#f28b82"></span>일별 평균 품절 빈도율 추이 (%)</div>', unsafe_allow_html=True)
        st.line_chart(df_stockout)
        st.markdown('</div>', unsafe_allow_html=True)
        
    # Top 10 Risk SKU 분석 테이블
    st.markdown("### Top 10 SCM Risk SKU 분석 (품절 취약 품목 집중 개선 실증)")
    st.info("Legacy SCM 체제 하에서 가장 빈번하게 품절이 발생하여 공급망 리스크를 유발했던 상위 10개 SKU를 추적하고, AI dynamic ROP/SS 최적화 도입 시의 개선율을 시각화합니다.")
    
    rows = "".join([
        f'<tr>'
        f'<td style="color:#8ab4f8;font-family:monospace;font-size:11px">{o["item_id"]}</td>'
        f'<td style="font-size:11px">{o["item_name"]}</td>'
        f'<td><span class="kb ok" style="font-size:10px">{o["category"]}</span></td>'
        f'<td style="font-family:monospace;font-size:11px">{o["store_id"]}</td>'
        f'<td style="color:#f28b82;font-weight:bold;text-align:center">{o["legacy_stockout_days"]}일</td>'
        f'<td style="color:#81c995;font-weight:bold;text-align:center">{o["ai_stockout_days"]}일</td>'
        f'<td style="color:#8ab4f8;font-weight:bold;text-align:right">+{o["improvement_pct"]:.1f}% 개선</td>'
        f'</tr>'
        for o in top_10
    ])
    
    st.markdown(f'''<div class="gt">
        <table>
            <thead>
                <tr>
                    <th>아이템 ID</th>
                    <th>아이템 명</th>
                    <th>카테고리</th>
                    <th>Walmart 매장</th>
                    <th style="text-align:center">Legacy 품절 일수</th>
                    <th style="text-align:center">AI SCM 품절 일수</th>
                    <th style="text-align:right">품절 예방 개선율</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
    </div>''', unsafe_allow_html=True)

def render_regional_dashboard():
    st.markdown(f'<div class="hdr"><div><div class="hdr-t">지역별 SCM 관제 센터</div><div class="hdr-s">지역별 재고 CRUD 및 기상 융합 인공지능 분석 관제탑</div></div></div>', unsafe_allow_html=True)
    
    # 1. 지역 등록 및 조회
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, region_name, region_code, description FROM regions ORDER BY region_name ASC")
        regions = [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        st.error(f"지역 데이터를 읽어오지 못했습니다: {e}")
        regions = []
    finally:
        conn.close()
    
    # 2단 레이아웃 (좌측: 지역 관리 및 데이터 업로드, 우측: 재고 모니터링 및 분석)
    col1, col2 = st.columns([1, 2.2])
    
    with col1:
        st.markdown('<div class="sec">지역 관리 & 데이터 수집</div>', unsafe_allow_html=True)
        
        # 신규 지역 등록
        with st.expander("➕ 신규 지역 등록", expanded=False):
            with st.form("new_region_form"):
                new_name = st.text_input("지역명 (예: 서울, 부산, 경기, 제주 등)")
                new_desc = st.text_input("설명 (예: 수도권 메인 기지)")
                submit_btn = st.form_submit_button("지역 등록")
                
                if submit_btn:
                    if not new_name.strip():
                        st.error("지역명을 입력해주세요.")
                    else:
                        try:
                            # 표준화 및 등록 시도
                            standardized_name, region_code = standardize_region(new_name)
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            cursor.execute(
                                "INSERT INTO regions (region_name, region_code, description) VALUES (?, ?, ?)",
                                (standardized_name, region_code, new_desc)
                            )
                            conn.commit()
                            st.success(f"지역 등록 완료: {standardized_name} ({region_code})")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("이미 등록된 지역 또는 코드입니다.")
                        except Exception as e:
                            st.error(f"등록 실패: {e}")
                        finally:
                            if 'conn' in locals() and conn:
                                conn.close()
                                
        if not regions:
            st.warning("⚠️ 등록된 지역이 없습니다. 먼저 지역을 등록해 주세요.")
            return
            
        # 지역 선택
        region_options = {f"{r['region_name']} ({r['region_code']})": r for r in regions}
        selected_key = st.selectbox("관제할 지역 선택", options=list(region_options.keys()))
        selected_region = region_options[selected_key]
        
        st.markdown(f"""
        <div class="kc" style="margin-bottom: 10px;">
            <div class="kl">선택된 지역 코드</div>
            <div class="kv b">{selected_region['region_code']}</div>
            <div class="ku">{selected_region['description'] or '설명 없음'}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # 데이터 업로드
        st.markdown('<div class="sec">SCM 엑셀/CSV 데이터 업로드</div>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader("지역 재고 및 수요 이력 업로드", type=["csv", "xlsx", "xls"], key="regional_uploader")
        
        if uploaded_file is not None:
            if st.button("🚀 데이터 파싱 및 라우팅 실행", key="btn_regional_route"):
                suffix = os.path.splitext(uploaded_file.name)[1]
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    shutil.copyfileobj(uploaded_file, tmp)
                    tmp_path = tmp.name
                    
                try:
                    stats = parse_and_route_file(tmp_path)
                    if stats["error_count"] == 0:
                        st.success(f"성공적으로 업로드 완료! ({stats['success_count']}행 적재)")
                    else:
                        st.warning(f"업로드 완료 (성공: {stats['success_count']}행, 실패: {stats['error_count']}행)")
                        with st.expander("실패 사유 보기"):
                            for err in stats["errors"]:
                                st.write(err)
                    st.rerun()
                except Exception as e:
                    st.error(f"파싱 실패: {e}")
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                        
    with col2:
        st.markdown('<div class="sec">실시간 지역 재고 흐름 & 기상 융합 분석</div>', unsafe_allow_html=True)
        
        # 1. 해당 지역 재고 데이터 조회
        conn = get_db_connection()
        inv_df = pd.read_sql_query(
            "SELECT product_name, date, quantity FROM region_inventory WHERE region_code = ? ORDER BY date ASC",
            conn, params=(selected_region["region_code"],)
        )
        
        # 2. 기상 데이터 조회
        weather_df = pd.read_sql_query(
            "SELECT date, temp, humidity, precipitation, weather_desc FROM weather_cache WHERE region_code = ? ORDER BY date ASC",
            conn, params=(selected_region["region_code"],)
        )
        conn.close()
        
        if inv_df.empty:
            st.info("💡 **[재고 데이터 없음]** 해당 지역에 적재된 SCM 재고 데이터가 없습니다. 좌측 드롭존을 통해 데이터를 먼저 업로드해 주세요.")
            return
            
        # 기상 정보가 비어있는 날짜가 있다면 실시간으로 기상 데이터 채우기 (캐싱 기동)
        unique_dates = inv_df["date"].unique()
        missing_weather_dates = [d for d in unique_dates if weather_df.empty or d not in weather_df["date"].values]
        
        if missing_weather_dates:
            with st.spinner("🌡️ 누락된 일별 외부 기상 데이터를 실시간 수집 및 캐싱 중..."):
                for d in missing_weather_dates:
                    try:
                        get_weather_for_region(selected_region["region_code"], d)
                    except Exception:
                        pass
            # 재조회
            conn = get_db_connection()
            weather_df = pd.read_sql_query(
                "SELECT date, temp, humidity, precipitation, weather_desc FROM weather_cache WHERE region_code = ? ORDER BY date ASC",
                conn, params=(selected_region["region_code"],)
            )
            conn.close()
            
        # 재고 KPI 카드 렌더링
        products = inv_df["product_name"].unique()
        total_qty = inv_df.groupby("product_name")["quantity"].last().sum() # 가장 최근 재고 합산
        
        st.markdown(f'''<div class="kg">
        <div class="kc"><div class="kl">모니터링 품목수</div><div class="kv">{len(products)} SKU</div><div class="ku">지정 품목 리스트</div></div>
        <div class="kc"><div class="kl">최신 총 재고량</div><div class="kv b">{total_qty:,.0f}</div><div class="ku">units (마지막 일자 기준)</div></div>
        <div class="kc"><div class="kl">기상 관측일수</div><div class="kv g">{len(weather_df)}일</div><div class="ku">동기화 완료</div></div>
        </div>''', unsafe_allow_html=True)
        
        # 품목 선택 필터
        selected_prod = st.selectbox("분석할 품목 선택", options=products)
        prod_inv = inv_df[inv_df["product_name"] == selected_prod]
        
        # 병합 데이터 생성
        merged = pd.merge(prod_inv, weather_df, on="date", how="inner")
        
        # 1. 재고 변동 차트 시각화
        st.markdown(f'<div class="cc"><div class="ct"><span class="dt" style="background:#8ab4f8"></span>[{selected_prod}] 일별 재고 변동 추이</div>', unsafe_allow_html=True)
        
        fig, ax = plt.subplots(figsize=(10, 2.8), dpi=100)
        fig.patch.set_facecolor(BG)
        ax.set_facecolor(BG)
        
        # X축 날짜 가독성 처리
        dates_parsed = pd.to_datetime(prod_inv["date"])
        ax.plot(dates_parsed, prod_inv["quantity"], color="#8ab4f8", lw=1.6, label="재고량")
        ax.fill_between(dates_parsed, prod_inv["quantity"], alpha=0.08, color="#8ab4f8")
        
        sax(ax)
        ax.set_xlabel("날짜 (Date)", fontsize=8)
        ax.set_ylabel("수량 (Units)", fontsize=8)
        fig.tight_layout(pad=0.5)
        st.pyplot(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # 2. 기상 융합 상관관계 분석
        st.markdown('<div class="sec">기상 융합 SCM 인공지능 상관분석</div>', unsafe_allow_html=True)
        
        if merged.empty or len(merged) < 3:
            st.warning("상관관계 분석을 수행하기 위한 데이터가 부족합니다. 최소 3일 이상의 일별 재고와 기상 매핑 데이터가 필요합니다.")
        else:
            # 피어슨 상관계수 산출
            corr_temp = merged["quantity"].corr(merged["temp"])
            corr_precip = merged["quantity"].corr(merged["precipitation"])
            
            def interpret_corr(val):
                if pd.isna(val): return "분석 불가"
                if abs(val) >= 0.7: return "매우 강력한 상관관계"
                if abs(val) >= 0.4: return "뚜렷한 상관관계"
                if abs(val) >= 0.1: return "약한 상관관계"
                return "상관성 없음 (독립적)"
                
            c_t_label = interpret_corr(corr_temp)
            c_p_label = interpret_corr(corr_precip)
            
            # HTML 카드형 레이아웃으로 변환 출력
            st.markdown(f"""
            <div class="kg">
                <div class="kc" style="border-left: 4px solid {CL['r'] if abs(corr_temp)>=0.4 else CL['d']}">
                    <div class="kl">기온(Temperature) 상관계수</div>
                    <div class="kv">{corr_temp:+.3f}</div>
                    <div class="ku">분석 결과: <b>{c_t_label}</b></div>
                </div>
                <div class="kc" style="border-left: 4px solid {CL['o'] if abs(corr_precip)>=0.4 else CL['d']}">
                    <div class="kl">강수량(Precipitation) 상관계수</div>
                    <div class="kv">{corr_precip:+.3f}</div>
                    <div class="ku">분석 결과: <b>{c_p_label}</b></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # 융합 차트 (이중축 시각화)
            st.markdown(f'<div class="cc"><div class="ct"><span class="dt" style="background:#fdd663"></span>[{selected_prod}] 재고량 vs 외부 환경 변수 (이중축 분석)</div>', unsafe_allow_html=True)
            
            fig_double, ax1 = plt.subplots(figsize=(10, 3.2), dpi=100)
            fig_double.patch.set_facecolor(BG)
            ax1.set_facecolor(BG)
            
            m_dates = pd.to_datetime(merged["date"])
            
            # Left axis: Inventory Qty
            ax1.plot(m_dates, merged["quantity"], color="#8ab4f8", lw=1.8, label="재고량")
            ax1.set_ylabel("재고량 (Units)", color="#8ab4f8", fontsize=8)
            ax1.tick_params(colors="#8ab4f8", labelsize=7)
            sax(ax1)
            
            # Right axis: Weather
            ax2 = ax1.twinx()
            weather_var = st.radio("이중축 플로팅 변수 선택", ["기온 (°C)", "강수량 (mm)"], horizontal=True, key="weather_axis_radio")
            
            if weather_var == "기온 (°C)":
                ax2.plot(m_dates, merged["temp"], color="#f28b82", lw=1.2, ls="--", label="기온 (°C)")
                ax2.set_ylabel("기온 (°C)", color="#f28b82", fontsize=8)
                ax2.tick_params(colors="#f28b82", labelsize=7)
            else:
                ax2.bar(m_dates, merged["precipitation"], color="#fdd663", alpha=0.4, width=0.6, label="강수량 (mm)")
                ax2.set_ylabel("강수량 (mm)", color="#fdd663", fontsize=8)
                ax2.tick_params(colors="#fdd663", labelsize=7)
                
            fig_double.tight_layout(pad=0.5)
            st.pyplot(fig_double, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # SCM 인공지능 예측 분석 코멘트
            st.markdown('<div class="sec">SCM AI 특이 지표 진단 보고서</div>', unsafe_allow_html=True)
            
            # 분석 리포트 자동 생성
            comments = []
            if corr_temp > 0.4:
                comments.append(f"📈 <b>온도 상승에 따른 재고 유입 증가:</b> 기온과 재고량이 뚜렷한 양의 상관관계({corr_temp:.2f})를 보입니다. 여름철 계절적 수요 급증에 대비해 선제적으로 안전 재고(Safety Stock)를 확보 중인 것으로 판단됩니다.")
            elif corr_temp < -0.4:
                comments.append(f"📉 <b>온도 상승에 따른 빠른 재고 소진:</b> 기온과 재고량이 강한 음의 상관관계({corr_temp:.2f})를 나타냅니다. 혹서기 수요 폭증으로 인한 품절(Stockout) 리스크가 우려되므로 재오더포인트(ROP)를 긴급히 높일 것을 권장합니다.")
                
            if corr_precip > 0.4:
                comments.append(f"🌧️ <b>우천 시 조달 리스크 대비 재고 비축:</b> 강수량과 재고량이 비례 관계({corr_precip:.2f})입니다. 물류 배송 지연 우려에 따라 선제적인 버퍼 재고 확보 정책이 작동하고 있습니다.")
            elif corr_precip < -0.4:
                comments.append(f"⚠️ <b>폭우 시 급격한 리드타임 지연 및 재고 고갈:</b> 강수량이 늘어날수록 재고량이 낮아지는 현상({corr_precip:.2f})이 발견됩니다. 폭우로 인한 조달 리드타임 지연이 실질적인 재고 소진으로 이어지고 있으므로 가드레일 승인 수량을 20% 긴급 증액해야 합니다.")
                
            if not comments:
                comments.append("✅ <b>안정 상태 유지:</b> 기상 변동에 따른 급격한 재고 변동 리스크가 발견되지 않았습니다. 현재의 자율 SCM 발주 정책이 기상 변수로부터 독립적으로 안정되게 제어되고 있습니다.")
                
            for comment in comments:
                st.markdown(f'<div class="ep en" style="border-left-color: #8ab4f8;"><div class="et">[AI 진단] SCM 의사결정 제언</div><div class="eb">{comment}</div></div>', unsafe_allow_html=True)

def main():
    st.sidebar.title("SCM 관제 시스템 메뉴")
    menu = st.sidebar.radio("이동", ["메인 대시보드", "지역별 SCM 관제 센터", "글로벌 공급망 리스크 관제탑"])
    
    # 운영 모드 투트랙 스위치 추가
    st.sidebar.markdown("---")
    st.sidebar.subheader("운영 모드 설정")
    op_mode = st.sidebar.radio("모드 선택", ["LIVE_MODE (실시간 관제)", "SIMULATION_MODE (시연용 스트레스 테스트)"])

    if menu == "메인 대시보드":
        if op_mode == "LIVE_MODE (실시간 관제)":
            # 1. 제로 마찰 자율 형식 업로드 엔진 & 가드레일 UI
            st.markdown(f'<div class="hdr"><div><div class="hdr-t">실시간 자율 AI 데이터 업로드 및 발주 제어</div><div class="hdr-s">비정형 텍스트 및 파일을 분석하여 안전 가드레일을 거쳐 즉시 발주를 실행합니다.</div></div></div>', unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("자연어 텍스트 입력")
                memo = st.text_area("발주 요청 사항을 자유롭게 적어주세요. (예: 반도체 칩 250개 입고 부탁드립니다.)", height=100)
            with c2:
                st.subheader("파일 드롭존 (CSV / Excel)")
                uploaded_file = st.file_uploader("발주서 파일을 업로드하세요.", type=["csv", "xlsx"])
                
            if st.button("AI 데이터 분석 및 정형화", key="btn_ai_parse"):
                parsed_res = None
                if uploaded_file is not None:
                    try:
                        if uploaded_file.name.endswith(".csv"):
                            df = pd.read_csv(uploaded_file)
                        else:
                            df = pd.read_excel(uploaded_file)
                        parsed_res = st.session_state["data_agent"].parse_unstructured_input(file_df=df)
                    except Exception as e:
                        st.error(f"파일을 읽는 도중 오류가 발생했습니다: {e}")
                elif memo.strip():
                    parsed_res = st.session_state["data_agent"].parse_unstructured_input(text=memo)
                else:
                    st.warning("자연어 텍스트를 입력하거나 파일을 업로드해 주세요.")
                    
                if parsed_res:
                    st.session_state["parsed_result"] = parsed_res
                    st.success("AI 비정형 데이터 분석 완료!")
                    
            # 분석 결과가 세션에 있으면 승인 UI 노출
            if "parsed_result" in st.session_state:
                res = st.session_state["parsed_result"]
                st.markdown(f"""
                <div class="kc" style="border-left: 5px solid #8ab4f8; margin: 10px 0;">
                    <h4 style="margin: 0 0 5px 0; color: #8ab4f8;">AI 분석 제안</h4>
                    <p style="margin: 3px 0; font-size: 13px;"><b>품목명:</b> {res['item_name']} | <b>수량:</b> {res['quantity']:,} 개 | <b>카테고리:</b> {res['category']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # 가드레일 임시 검증용
                is_safe, guardrail_reason = st.session_state["action_agent"].validate_guardrails(res['item_name'], res['quantity'])
                if not is_safe:
                    st.error(f"가드레일 위반 경고: {guardrail_reason}")
                else:
                    st.success("비즈니스 가드레일 통과! 안전한 발주 요청입니다.")
                    if st.button("최종 발주 승인 및 집행", key="btn_confirm_order"):
                        exec_res = st.session_state["action_agent"].execute_and_publish(
                            res['item_name'], res['quantity'], res['category']
                        )
                        if exec_res["status"] == "APPROVED":
                            st.balloons()
                            st.success(f"발주서 발행 및 집행 성공! (발주 ID: {exec_res['order_id']})")
                            # 세션 초기화
                            del st.session_state["parsed_result"]
                        else:
                            st.error(f"발주 실패: {exec_res['reason']}")
            
            # 기존 메인 대시보드 렌더링 (실시간 관제 기능 보존)
            st.markdown("---")
            st.subheader("실시간 SCM 관제 센터")
            render_main_dashboard()
            
        else:
            # SIMULATION_MODE 렌더링
            render_simulation_dashboard()
            
    elif menu == "지역별 SCM 관제 센터":
        render_regional_dashboard()
        
    elif menu == "글로벌 공급망 리스크 관제탑":
        st.markdown(f'<div class="hdr"><div><div class="hdr-t">글로벌 공급망 리스크 관제탑</div><div class="hdr-s">Global Supply Chain Risk Control Tower &nbsp;·&nbsp; 실시간 국가별 거점 리스크 및 기상 관제</div></div></div>',unsafe_allow_html=True)
        
        wmo_master_df = load_wmo_master()
        available_countries = [c for c in sorted(wmo_master_df['country'].dropna().unique()) if c != "Malaysia"]
        
        col_sel1, col_sel2 = st.columns(2)
        selected_country = col_sel1.selectbox("대상 국가", options=available_countries, index=available_countries.index("South Korea") if "South Korea" in available_countries else 0)
        filtered_stations = wmo_master_df[wmo_master_df['country'] == selected_country]
        selected_station_name = col_sel2.selectbox(f"{selected_country} 내 허브 거점", options=filtered_stations['station_name'])
        
        matched_station = filtered_stations[filtered_stations['station_name'] == selected_station_name].iloc[0]
        
        st.info(f"**[SCM 제어 시스템]** 관제 타겟: **{matched_station['station_name']} ({selected_country})** | 위치: `{matched_station['latitude']} / {matched_station['longitude']}`")
        
        st.markdown("---")
        
        # 1~3. 외부 실시간 데이터 수집 (백그라운드 워커 파일에서 읽기)
        from utils.state_manager import load_lkv
        lkv_state = load_lkv()
        country_data = lkv_state.get(selected_country, {})
        
        raw_weather = country_data.get("weather", "[Fallback] 대체 기상 정보")
        data_vector = country_data.get("macro", {"oil_change_pct": 0.0, "inflation_rate": 2.0, "index_change_pct": 0.0, "fx_change_pct": 0.0})
        gdelt_info = country_data.get("gdelt", {"average_tone": 0.0, "risk_level": "Low", "top_headline": "Fallback Mode"})
        trend_info = country_data.get("trends", {"composite_score": 0.0, "matched_count": 0})
        
        # 데이터가 아예 없는 경우 (첫 실행 등) fallback_mode 처리
        fallback_mode = "macro" not in country_data or "gdelt" not in country_data
        
        if fallback_mode:
            st.warning("⚠️ **[FALLBACK_MODE_ACTIVATED]** 백그라운드 수집 데이터가 없어 기본값으로 연산된 점수입니다.")
        else:
            st.success(f"ℹ️ **[데이터 신선도]** 마지막 동기화 시점: `{country_data.get('timestamp', 'N/A')}`")

        gdelt_tone = gdelt_info.get("average_tone", 0.0)
        gdelt_risk_level = gdelt_info.get("risk_level", "Low")
        gdelt_headline = gdelt_info.get("top_headline", "")
        social_score = trend_info.get("composite_score", 0.0)
                
        # 4. 실시간 물류 리스크 점수화 엔진 실행
        scorer = LogisticsRiskScorer()
        scm_metrics = scorer.score_all(
            data_vector=data_vector,
            weather_text=raw_weather,
            trend_score=social_score,
            gdelt_tone=gdelt_tone
        )
        
        # 5. SCM 리스크 파급 효과 예상 화면 구성 (Raw Data 및 원문 텍스트는 전면 은닉)
        st.markdown(f"### 🚚 {selected_country} 중심 글로벌 공급망 리스크 파급 예상")
        st.info("💡 **[공급망 분석 안내]** 본 관제탑은 원시 금융 지표(환율/유가/지수) 및 기상청 원문 데이터를 제거하고, SCM 물류 파급력을 수학적으로 정밀 계량화한 실질 예상치만을 노출합니다.")
        
        # 1계층: 종합 리스크 스코어 & 조달 지연일
        r_col1, r_col2 = st.columns(2)
        
        # SCM 종합 리스크 스코어 (로지스틱 시그모이드 모델링)
        r_score = scm_metrics["integrated_risk_score"]
        r_level = "심각 (CRITICAL)" if r_score >= 70 else ("경고 (WARNING)" if r_score >= 40 else "정상 (NORMAL)")
        r_color = "#f28b82" if r_score >= 70 else ("#fdd663" if r_score >= 40 else "#81c995")
        
        r_col1.markdown(f"""
        <div class="kc" style="border-left: 5px solid {r_color}; padding: 15px;">
            <div class="kl">SCM 종합 리스크 스코어 (Sigmoid Mapping)</div>
            <div class="kv" style="color: {r_color}; font-size: 32px; font-weight: bold;">{r_score} / 100</div>
            <div class="ku" style="font-size: 11px; margin-top: 5px;">현재 리스크 수준: <b>{r_level}</b></div>
        </div>
        """, unsafe_allow_html=True)
        
        # 예상 조달 지연일 (LT delay)
        lt_delay = scm_metrics["lead_time_delay"]
        lt_color = "#f28b82" if lt_delay >= 2.0 else ("#fdd663" if lt_delay >= 0.5 else "#81c995")
        r_col2.markdown(f"""
        <div class="kc" style="border-left: 5px solid {lt_color}; padding: 15px;">
            <div class="kl">예상 조달 지연일 (Lead Time Delay)</div>
            <div class="kv" style="color: {lt_color}; font-size: 32px; font-weight: bold;">+{lt_delay} Days</div>
            <div class="ku" style="font-size: 11px; margin-top: 5px;">실시간 수집된 날씨 점수: <b>{scm_metrics['weather_score']:.1f}점</b> 반영됨</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        
        # 2계층: 운임 변동률, 수요 충격 지수, 사회적 리스크
        e_col1, e_col2, e_col3 = st.columns(3)
        
        # 예상 물류 운임 변동률 (Cf)
        cf = scm_metrics["freight_rate_change"]
        cf_color = "#f28b82" if cf >= 15.0 else ("#fdd663" if cf >= 5.0 else "#81c995")
        cf_sign = "+" if cf >= 0 else ""
        e_col1.markdown(f"""
        <div class="kc" style="border-left: 5px solid {cf_color};">
            <div class="kl">예상 물류 운임 변동률 (Freight Impact)</div>
            <div class="kv" style="color: {cf_color};">{cf_sign}{cf:.2f}%</div>
            <div class="ku">WTI 유가 변동률 및 CPI 인플레이션율 연동</div>
        </div>
        """, unsafe_allow_html=True)
        
        # 소비자 수요 충격 지수 (Ds)
        ds = scm_metrics["demand_shock_index"]
        ds_color = "#f28b82" if ds <= -10.0 else ("#fdd663" if ds <= -2.0 else "#81c995")
        ds_sign = "+" if ds >= 0 else ""
        e_col2.markdown(f"""
        <div class="kc" style="border-left: 5px solid {ds_color};">
            <div class="kl">소비자 수요 충격 예상치 (Demand Shock)</div>
            <div class="kv" style="color: {ds_color};">{ds_sign}{ds:.2f}%</div>
            <div class="ku">주가지수/환율 로그 탄력성 모델 반영</div>
        </div>
        """, unsafe_allow_html=True)
        
        # 사회적/지정학적 리스크 점수
        social_risk = scm_metrics["social_score"]
        social_color = "#f28b82" if social_risk >= 50.0 else ("#fdd663" if social_risk >= 20.0 else "#81c995")
        e_col3.markdown(f"""
        <div class="kc" style="border-left: 5px solid {social_color};">
            <div class="kl">사회적/지정학적 리스크 (Social Risk)</div>
            <div class="kv" style="color: {social_color};">{social_risk:.1f} 점</div>
            <div class="ku">GDELT ({gdelt_risk_level}) 및 구글 트렌드 실시간 융합</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        
        # GDELT 미디어 헤드라인 요약 노출
        if gdelt_headline and gdelt_headline != "No critical event":
            st.warning(f"🚨 **[지정학적 리스크 헤드라인 실시간 감지]** {gdelt_headline} (GDELT Sentiment Tone: {gdelt_tone})")

if __name__=="__main__": main()
