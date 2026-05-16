import json, os, sys, pandas as pd, numpy as np, matplotlib.pyplot as plt
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
from matplotlib import rc
import streamlit as st

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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
import cloudscraper
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

ssl._create_default_https_context = ssl._create_unverified_context

def _selenium_crawl_table(url):
    """Selenium 공용 테이블 크롤러 (TradingEconomics용)"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    try:
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(15)
        driver.get(url)
        html = driver.page_source
        driver.quit()
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        if not table: return None
        rows_data = []
        for row in table.find_all("tr"):
            cols = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
            if len(cols) > 2: rows_data.append(cols)
        if rows_data:
            df = pd.DataFrame(rows_data)
            df.columns = df.iloc[0]
            return df[1:].reset_index(drop=True)
    except: pass
    return None

@st.cache_data(ttl=600, show_spinner=False)
def crawl_te_inflation():
    df = _selenium_crawl_table("https://ko.tradingeconomics.com/country-list/inflation-rate?continent=world")
    if df is None: raise ValueError("TE Inflation table empty")
    return df

@st.cache_data(ttl=600, show_spinner=False)
def crawl_te_interest_rate():
    df = _selenium_crawl_table("https://ko.tradingeconomics.com/country-list/interest-rate?continent=world")
    if df is None: raise ValueError("TE Rate table empty")
    return df

@st.cache_data(ttl=600, show_spinner=False)
def crawl_investing_indices():
    """Investing.com 주요지수 크롤러 (cloudscraper - Cloudflare 우회)"""
    url = "https://kr.investing.com/indices/major-indices"
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    try:
        resp = scraper.get(url, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            table = soup.find("table")
            if not table: raise ValueError("Investing table empty")
            rows_data = []
            for row in table.find_all("tr"):
                cols = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
                if len(cols) > 2: rows_data.append(cols)
            if rows_data:
                df = pd.DataFrame(rows_data)
                df.columns = df.iloc[0]
                return df[1:].reset_index(drop=True)
    except: pass
    raise ValueError("Investing crawl failed")

# --- [내장형 매크로 엔진] ---
class LocalMacroEngine:
    def __init__(self):
        pass

    def fetch_unified_macro_vector(self, country_name):
        # WTI 유가 (yfinance)
        wti_oil_price, wti_oil_change = 0.0, 0.0
        try:
            oil_hist = yf.download("CL=F", period="7d", progress=False)
            if not oil_hist.empty and 'Close' in oil_hist.columns:
                cd = oil_hist['Close'].iloc[:, 0] if isinstance(oil_hist['Close'], pd.DataFrame) else oil_hist['Close']
                cd = cd.sort_index()
                if len(cd) >= 2:
                    wti_oil_price = float(cd.iloc[-1])
                    wti_oil_change = ((wti_oil_price - float(cd.iloc[-2])) / float(cd.iloc[-2])) * 100
        except: pass

        # 국가별 레지스트리: kr_idx = Investing.com 한글 종목명, te_country = TE 한글 국명, yf_idx = 백업용 야후파이낸스
        country_registry = {
            "Argentina": {"fx": "USDARS=X", "kr_idx": "메르발", "te_country": "아르헨티나", "currency": "ARS", "yf_idx": "^MERV"},
            "Australia": {"fx": "AUDUSD=X", "kr_idx": "호주 S&P/ASX", "te_country": "호주", "currency": "AUD", "yf_idx": "^AXJO"},
            "Belgium": {"fx": "EURUSD=X", "kr_idx": "벨기에 BELderived", "te_country": "벨기에", "currency": "EUR", "yf_idx": "^BFX"},
            "Brazil": {"fx": "USDBRL=X", "kr_idx": "브라질 보베스파", "te_country": "브라질", "currency": "BRL", "yf_idx": "^BVSP"},
            "Canada": {"fx": "USDCAD=X", "kr_idx": "캐나다 S&P/TSX", "te_country": "캐나다", "currency": "CAD", "yf_idx": "^GSPTSE"},
            "China": {"fx": "USDCNY=X", "kr_idx": "상해종합", "te_country": "중국", "currency": "CNY", "yf_idx": "000001.SS"},
            "Egypt": {"fx": "USDEGP=X", "kr_idx": "EGX 30", "te_country": "이집트", "currency": "EGP", "yf_idx": None},
            "France": {"fx": "EURUSD=X", "kr_idx": "프랑스 CAC", "te_country": "프랑스", "currency": "EUR", "yf_idx": "^FCHI"},
            "Germany": {"fx": "EURUSD=X", "kr_idx": "DAXderived", "te_country": "독일", "currency": "EUR", "yf_idx": "^GDAXI"},
            "India": {"fx": "USDINR=X", "kr_idx": "인도 센섹스", "te_country": "인도", "currency": "INR", "yf_idx": "^BSESN"},
            "Indonesia": {"fx": "USDIDR=X", "kr_idx": "인도네시아 IDX", "te_country": "인도네시아", "currency": "IDR", "yf_idx": "^JKSE"},
            "Italy": {"fx": "EURUSD=X", "kr_idx": "이탈리아 FTSE MIBderived", "te_country": "이탈리아", "currency": "EUR", "yf_idx": "FTSEMIB.MI"},
            "Japan": {"fx": "USDJPY=X", "kr_idx": "닛케이derived", "te_country": "일본", "currency": "JPY", "yf_idx": "^N225"},
            "Mexico": {"fx": "USDMXN=X", "kr_idx": "S&P/BMV IPC", "te_country": "멕시코", "currency": "MXN", "yf_idx": "^MXX"},
            "Netherlands": {"fx": "EURUSD=X", "kr_idx": "네덜란드 AEX", "te_country": "네덜란드", "currency": "EUR", "yf_idx": "^AEX"},
            "New Zealand": {"fx": "NZDUSD=X", "kr_idx": "뉴질랜드 50", "te_country": "뉴질랜드", "currency": "NZD", "yf_idx": "^NZ50"},
            "Philippines": {"fx": "USDPHP=X", "kr_idx": "PSEi Composite", "te_country": "필리핀", "currency": "PHP", "yf_idx": "PSEI.PS"},
            "Saudi Arabia": {"fx": "USDSAR=X", "kr_idx": "사우디아라비아 Tadawul", "te_country": "사우디 아라비아", "currency": "SAR", "yf_idx": "^TASI.SR"},
            "South Africa": {"fx": "USDZAR=X", "kr_idx": "남아프리카 Top 40", "te_country": "남아프리카 공화국", "currency": "ZAR", "yf_idx": "^J203.JO"},
            "South Korea": {"fx": "USDKRW=X", "kr_idx": "코스피지수", "te_country": "대한민국", "currency": "KRW", "yf_idx": "^KS11"},
            "Spain": {"fx": "EURUSD=X", "kr_idx": "스페인 IBEXderived", "te_country": "스페인", "currency": "EUR", "yf_idx": "^IBEX"},
            "Switzerland": {"fx": "USDCHF=X", "kr_idx": "스위스 SMIderived", "te_country": "스위스", "currency": "CHF", "yf_idx": "^SSMI"},
            "Taiwan": {"fx": "USDTWD=X", "kr_idx": "대만 가권", "te_country": "대만", "currency": "TWD", "yf_idx": "^TWII"},
            "Thailand": {"fx": "USDTHB=X", "kr_idx": "SET", "te_country": "태국", "currency": "THB", "yf_idx": "^SET.BK"},
            "Turkey": {"fx": "USDTRY=X", "kr_idx": "터키 BIST", "te_country": "터키", "currency": "TRY", "yf_idx": "XU100.IS"},
            "United Arab Emirates": {"fx": "USDAED=X", "kr_idx": "DFM 일반", "te_country": "아랍 에미리트", "currency": "AED", "yf_idx": None},
            "United Kingdom": {"fx": "GBPUSD=X", "kr_idx": "영국 FTSEderived", "te_country": "연합 왕국", "currency": "GBP", "yf_idx": "^FTSE"},
            "United States": {"fx": None, "kr_idx": "S&P 500derived", "te_country": "미국", "currency": "USD", "yf_idx": "^GSPC"},
            "Vietnam": {"fx": "USDVND=X", "kr_idx": "VN 30", "te_country": "베트남", "currency": "VND", "yf_idx": "^VNINDEX.HM"},
            "Singapore": {"fx": "USDSGD=X", "kr_idx": None, "te_country": "싱가포르", "currency": "SGD", "yf_idx": "^STI"},
        }
        cfg = country_registry.get(country_name, {"fx": None, "kr_idx": None, "te_country": None, "currency": "Unknown", "yf_idx": None})

        # (A) 환율 (yfinance)
        fx_val, fx_chg = 1.0, 0.0
        if cfg["fx"]:
            try:
                fh = yf.download(cfg["fx"], period="7d", progress=False)
                if not fh.empty and 'Close' in fh.columns:
                    cd = fh['Close'].iloc[:, 0] if isinstance(fh['Close'], pd.DataFrame) else fh['Close']
                    cd = cd.sort_index()
                    if len(cd) >= 2:
                        fx_val = float(cd.iloc[-1])
                        fx_chg = ((fx_val - float(cd.iloc[-2])) / float(cd.iloc[-2])) * 100
            except: pass

        # (B) 주가지수 (Investing.com 크롤링) -> 실패/부재 시 yfinance 폴백
        idx_val, idx_chg = 0.0, 0.0
        idx_display_name = cfg.get("kr_idx")
        if idx_display_name:
            try:
                scraped_idx = crawl_investing_indices()
                if scraped_idx is not None and '종목명' in scraped_idx.columns:
                    matched = scraped_idx[scraped_idx['종목명'] == idx_display_name]
                    if not matched.empty:
                        idx_val = float(matched.iloc[0]['종가'].replace(',', ''))
                        idx_chg = float(matched.iloc[0]['변동 %'].replace('%', '').replace('+', ''))
            except: pass
            
        if idx_val == 0.0 and cfg.get("yf_idx"):
            try:
                yh = yf.download(cfg["yf_idx"], period="7d", progress=False)
                if not yh.empty and 'Close' in yh.columns:
                    cd = yh['Close'].iloc[:, 0] if isinstance(yh['Close'], pd.DataFrame) else yh['Close']
                    cd = cd.sort_index()
                    if len(cd) >= 2:
                        idx_val = float(cd.iloc[-1])
                        idx_chg = ((idx_val - float(cd.iloc[-2])) / float(cd.iloc[-2])) * 100
            except: pass

        # (C) 기준금리 (TradingEconomics 크롤링)
        domestic_rate = None
        te_name = cfg.get("te_country")
        eurozone_countries = ["독일", "프랑스", "스페인", "벨기에", "이탈리아", "네덜란드"]
        rate_te_name = "유럽​​ 지역" if te_name in eurozone_countries else te_name

        if rate_te_name:
            try:
                scraped_rate = crawl_te_interest_rate()
                if scraped_rate is not None and '국가' in scraped_rate.columns:
                    matched = scraped_rate[scraped_rate['국가'] == rate_te_name]
                    if not matched.empty:
                        domestic_rate = float(matched.iloc[0]['마지막'])
            except: pass

        # (D) 물가상승률 (TradingEconomics 크롤링)
        domestic_inflation = None
        if te_name:
            try:
                scraped_inf = crawl_te_inflation()
                if scraped_inf is not None and '국가' in scraped_inf.columns:
                    matched = scraped_inf[scraped_inf['국가'] == te_name]
                    if not matched.empty:
                        domestic_inflation = float(matched.iloc[0]['마지막'])
            except: pass

        calculated_risk = min(100.0, max(0.0, (abs(fx_chg) * 30 + abs(idx_chg) * 30 + abs(wti_oil_change) * 40)))
        clean_idx_name = idx_display_name.replace('derived', '') if idx_display_name else None

        return {
            "country": country_name, "currency_code": cfg["currency"], "fx_ticker": cfg["fx"],
            "fx_value": round(fx_val, 2), "fx_change_pct": round(fx_chg, 2), "index_ticker": clean_idx_name,
            "index_value": round(idx_val, 2), "index_change_pct": round(idx_chg, 2),
            "oil_price": round(wti_oil_price, 2), "oil_change_pct": round(wti_oil_change, 2),
            "interest_rate": round(domestic_rate, 2) if domestic_rate is not None else None,
            "inflation_rate": round(domestic_inflation, 2) if domestic_inflation is not None else None,
            "integrated_risk_score": round(calculated_risk, 2),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

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

def get_live_weather_by_station(station_id):
    utc_now = datetime.now(datetime.timezone.utc) if hasattr(datetime, 'timezone') else datetime.utcnow()
    target_time = (utc_now - pd.Timedelta(hours=2)).strftime("%Y%m%d%H00")
    kma_key = st.secrets.get("KMA_AUTH_KEY", os.environ.get("KMA_AUTH_KEY", ""))
    params = {"tm": target_time, "dtm": "3", "stn": int(station_id), "help": "0", "authKey": kma_key}
    try:
        response = requests.get(url, params=params, timeout=7)
        return response.text if response.status_code == 200 else "⚠️ 기상 데이터 지연"
    except: return "🚨 기상 스트림 통신 오류"

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
        
        macro_engine = LocalMacroEngine()
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
        st.code(get_live_weather_by_station(matched_station['station_id']), language="text")

if __name__=="__main__": main()
