import json, os, sys, pandas as pd, numpy as np, matplotlib.pyplot as plt
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
from matplotlib import rc
import streamlit as st
from utils.macro_connector import GlobalMacroEngine
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

def main():
    st.sidebar.title("SCM 관제 시스템 메뉴")
    menu = st.sidebar.radio("이동", ["메인 대시보드", "글로벌 공급망 리스크 관제탑"])
    
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
        st.markdown(f"### {selected_country} 중심 공급망 리스크 벡터")
        
        macro_engine = GlobalMacroEngine()
        data_vector = macro_engine.fetch_unified_macro_vector(selected_country)
        
        # 1계층 지표
        st.subheader("1계층: 실물 경기 및 금융 변동성 벡터")
        m_col1, m_col2, m_col3 = st.columns(3)
        fx_label = f"대미 환율 ({data_vector['currency_code']}/USD)" if data_vector['fx_ticker'] else "기준 통화 (USD)"
        m_col1.metric(label=fx_label, value=f"{data_vector['fx_value']}", delta=f"{data_vector['fx_change_pct']}%")
        
        idx_label = f"시장 지수 ({data_vector['index_ticker']})" if data_vector['index_ticker'] else "시장 지수"
        idx_val = f"{data_vector['index_value']} pt" if data_vector['index_value'] > 0 else "데이터 준비 중"
        m_col2.metric(label=idx_label, value=idx_val, delta=f"{data_vector['index_change_pct']}%")
        m_col3.metric(label="WTI 국제 유가", value=f"${data_vector['oil_price']}", delta=f"{data_vector['oil_change_pct']}%", delta_color="inverse")
            
        # 2계층 지표
        st.subheader("2계층: 통화 정책 및 내수 인플레이션 벡터")
        e_col1, e_col2, e_col3 = st.columns(3)
        
        rate_display = f"{data_vector['interest_rate']}%" if data_vector['interest_rate'] is not None else "N/A (미제공)"
        e_col1.metric(label=f"{selected_country} 고유 기준금리", value=rate_display, delta="FRED 고유국가 직접 동기화")
        
        inf_display = f"{data_vector['inflation_rate']:.2f}%" if data_vector['inflation_rate'] is not None else "N/A (미제공)"
        e_col2.metric(label=f"{selected_country} 소비자물가상승률(YoY)", value=inf_display, delta="실질 변동률 정제 완료")
        
        e_col3.metric(label="종합 위험 스코어", value=f"{data_vector['integrated_risk_score']} / 100")
            
        st.markdown("---")
        st.markdown("### 기상청 GTS 실시간 수집 RAW 전문 스트림")
        st.code(get_live_weather_by_station(matched_station['station_id'], matched_station['latitude'], matched_station['longitude']), language="text")

if __name__=="__main__": main()
