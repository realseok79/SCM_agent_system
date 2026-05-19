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

@st.cache_data(ttl=3)
def get_db_summary():
    """
    SQLite DB에서 실제 등록 지점 및 전체 품목 현황을 실시간 집계합니다.
    """
    conn = get_db_connection()
    try:
        # 1. 지점 수
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM regions")
        region_count = cursor.fetchone()[0]
        
        # 2. 총 모니터링 품목(SKU) 수
        cursor.execute("SELECT COUNT(DISTINCT product_name) FROM region_inventory")
        sku_count = cursor.fetchone()[0]
        
        # 3. 최신 총 재고량 (각 지점별 가장 최근 날짜의 품목별 재고 합산)
        cursor.execute("""
            SELECT SUM(quantity) FROM region_inventory i
            WHERE date = (
                SELECT MAX(date) FROM region_inventory WHERE region_code = i.region_code AND product_name = i.product_name
            )
        """)
        row = cursor.fetchone()
        total_stock = row[0] if row and row[0] is not None else 0.0
        
        # 4. 오늘 발주 경고가 뜬 품목 수 (평균 재고량 대비 30% 이하인 고갈 품목들)
        cursor.execute("""
            SELECT COUNT(*) FROM (
                SELECT region_code, product_name, quantity,
                       (SELECT AVG(quantity) FROM region_inventory WHERE region_code = i.region_code AND product_name = i.product_name) as avg_qty
                FROM region_inventory i
                WHERE date = (
                    SELECT MAX(date) FROM region_inventory WHERE region_code = i.region_code AND product_name = i.product_name
                )
            ) WHERE quantity < avg_qty * 0.3
        """)
        alert_count = cursor.fetchone()[0]
        
        # 5. 오늘 기상 이변 발생 지점 수 (강수량이 10mm 이상이거나 기온이 30도 이상 / 0도 이하인 곳)
        cursor.execute("""
            SELECT COUNT(DISTINCT region_code) FROM weather_cache w
            WHERE date = (SELECT MAX(date) FROM weather_cache WHERE region_code = w.region_code)
              AND (precipitation >= 10.0 OR temp >= 30.0 OR temp <= 0.0)
        """)
        weather_alerts = cursor.fetchone()[0]
        
        # 6. 지점별 최신 재고 상세 집계
        cursor.execute("""
            SELECT r.region_name, r.region_code, 
                   COUNT(DISTINCT i.product_name) as sku_count,
                   SUM(i.quantity) as total_qty,
                   MAX(i.date) as last_update
            FROM regions r
            LEFT JOIN region_inventory i ON r.region_code = i.region_code
            AND i.date = (
                SELECT MAX(date) FROM region_inventory WHERE region_code = r.region_code AND product_name = i.product_name
            )
            GROUP BY r.region_code
            ORDER BY total_qty DESC
        """)
        region_rows = [dict(row) for row in cursor.fetchall()]
        
        # 7. 기상이변 상세 지점 리스트
        cursor.execute("""
            SELECT r.region_name, w.temp, w.precipitation, w.weather_desc, w.date
            FROM regions r
            JOIN weather_cache w ON r.region_code = w.region_code
            WHERE w.date = (SELECT MAX(date) FROM weather_cache WHERE region_code = r.region_code)
              AND (w.precipitation >= 10.0 OR w.temp >= 30.0 OR w.temp <= 0.0)
        """)
        weather_alert_details = [dict(row) for row in cursor.fetchall()]
        
        return {
            "region_count": region_count,
            "sku_count": sku_count,
            "total_stock": total_stock,
            "alert_count": alert_count,
            "weather_alerts": weather_alerts,
            "region_rows": region_rows,
            "weather_alert_details": weather_alert_details
        }
    except Exception as e:
        print(f"⚠️ get_db_summary 실패: {e}")
        return {
            "region_count": 0, "sku_count": 0, "total_stock": 0.0, "alert_count": 0, "weather_alerts": 0,
            "region_rows": [], "weather_alert_details": []
        }
    finally:
        conn.close()

def c_total_stock_trend():
    """
    최근 7일간 전체 등록 지점의 합산 재고량 추이를 그립니다.
    """
    conn = get_db_connection()
    try:
        df = pd.read_sql_query("""
            SELECT date, SUM(quantity) as total_qty
            FROM region_inventory
            GROUP BY date
            ORDER BY date DESC
            LIMIT 7
        """, conn)
        if df.empty:
            return None
        df = df.iloc[::-1]  # X축 시간순 정렬
        f, ax = mk(2.2)
        ax.plot(df["date"], df["total_qty"], color=CL["s"], lw=1.8, marker="o", label="전체 재고 합계")
        ax.fill_between(df["date"], df["total_qty"], alpha=0.08, color=CL["s"])
        sax(ax)
        ax.set_xlabel("일자 (Date)", fontsize=8)
        ax.set_ylabel("수량 (Units)", fontsize=8)
        ax.legend(fontsize=7, framealpha=0, loc="upper left", labelcolor=TX)
        f.tight_layout(pad=0.5)
        return f
    except Exception as e:
        print(f"⚠️ c_total_stock_trend 실패: {e}")
        return None
    finally:
        conn.close()

def render_home_dashboard():
    """
    메인 화면: SQLite DB의 실제 지점 정보와 재고 데이터를 집계하여 대시보드로 표출합니다.
    """
    st_autorefresh(interval=3000, key="scm_home_refresh") # 3초 자동 새로고침
    summary = get_db_summary()
    
    # ROW 0: Header
    st.markdown(f'<div class="hdr"><div><div class="hdr-t">Enterprise SCM 자율 의사결정 관제탑</div><div class="hdr-s">실시간 SQLite 데이터베이스 기반 등록 지점 및 통합 SCM 지표 &nbsp;·&nbsp; {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div></div></div>', unsafe_allow_html=True)
    
    # ROW 1: KPI Cards
    st.markdown(f'''<div class="kg">
<div class="kc"><div class="kl">등록 지점 수</div><div class="kv b">{summary["region_count"]} 개소</div><div class="ku">실무 가용 물류 거점</div></div>
<div class="kc"><div class="kl">전체 모니터링 SKU</div><div class="kv">{summary["sku_count"]} 품목</div><div class="ku">등록된 활성 상품 종류</div></div>
<div class="kc"><div class="kl">통합 가용 재고량</div><div class="kv g">{summary["total_stock"]:,.0f} 개</div><div class="ku">지점별 최신 재고 합산</div></div>
<div class="kc"><div class="kl">발주 경고 SKU</div><div class="kv {"r" if summary["alert_count"] > 0 else "g"}">{summary["alert_count"]} 품목</div><div class="ku">평균 대비 30% 이하 고갈 품목</div><div class="kb {"w" if summary["alert_count"] > 0 else "ok"}">{"경고" if summary["alert_count"] > 0 else "정상"}</div></div>
<div class="kc"><div class="kl">기상 이변 거점</div><div class="kv {"y" if summary["weather_alerts"] > 0 else "g"}">{summary["weather_alerts"]} 개소</div><div class="ku">강수/온도 경보 발령</div><div class="kb {"w" if summary["weather_alerts"] > 0 else "ok"}">{"기상 악화" if summary["weather_alerts"] > 0 else "정상"}</div></div>
</div>''', unsafe_allow_html=True)

    r2a, r2b = st.columns([1.5, 1])
    
    with r2a:
        st.markdown('<div class="cc"><div class="ct"><span class="dt" style="background:#8ab4f8"></span>등록 지점별 최신 재고 현황</div>', unsafe_allow_html=True)
        if summary["region_rows"]:
            rows = ""
            for r in summary["region_rows"]:
                qty = r["total_qty"] if r["total_qty"] is not None else 0.0
                rows += f'''<tr>
                    <td style="color:#8ab4f8;font-weight:bold;">{r["region_name"]}</td>
                    <td style="font-family:monospace;">{r["region_code"]}</td>
                    <td>{r["sku_count"]} SKU</td>
                    <td style="font-weight:bold;color:#81c995;">{qty:,.0f} ea</td>
                    <td style="color:#9aa0a6;font-size:10px;">{r["last_update"] or "데이터 없음"}</td>
                </tr>'''
            st.markdown(f'''<div class="gt" style="max-height:260px;overflow-y:auto;width:100%;">
                <table><thead><tr><th>지점명</th><th>지역 코드</th><th>모니터링 SKU</th><th>최신 총 재고량</th><th>마지막 동기화</th></tr></thead>
                <tbody>{rows}</tbody></table></div>''', unsafe_allow_html=True)
        else:
            st.markdown('<div class="ep ew"><div class="et">등록된 지점이 없습니다.</div><div class="eb">상단의 [지역별 SCM 관제 센터] 메뉴 또는 하단의 엑셀/CSV 업로더를 통해 지점과 재고를 먼저 등록해 주세요.</div></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with r2b:
        st.markdown('<div class="cc"><div class="ct"><span class="dt" style="background:#fdd663"></span>지점 기상 경보 및 이변 상황</div>', unsafe_allow_html=True)
        if summary["weather_alert_details"]:
            for w in summary["weather_alert_details"]:
                st.markdown(f'''<div class="ep ec">
                    <div class="et">🚨 {w["region_name"]} 기상 이변 발생 ({w["date"]})</div>
                    <div class="eb">기온: {w["temp"]}°C | 강수량: {w["precipitation"]}mm ({w["weather_desc"]})<br/><b>물류 지연 위험:</b> 조달 리드타임에 영향을 줄 수 있으므로 실시간 관제가 요구됩니다.</div>
                </div>''', unsafe_allow_html=True)
        else:
            st.markdown('<div class="ep en"><div class="et">✅ 전 지점 기상 안정</div><div class="eb">현재 기상 이변(폭우/태풍/혹한/혹서)이 감지된 지점이 없으며, 모든 물류 경로가 원활하게 가동 중입니다.</div></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
    st.markdown('<div class="cc"><div class="ct"><span class="dt" style="background:#8ab4f8"></span>최근 7일간 전체 재고 추이 (통합 흐름)</div>', unsafe_allow_html=True)
    fig_trend = c_total_stock_trend()
    if fig_trend:
        st.pyplot(fig_trend, use_container_width=True)
    else:
        st.info("💡 **[추이 분석 대기]** 재고 변동 차트를 그리기 위한 데이터가 부족합니다. 매일 재고를 업데이트하면 7일 추이 그래프가 나타납니다.")
    st.markdown('</div>', unsafe_allow_html=True)

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
            
            corr_temp_str = f"{corr_temp:+.3f}" if not pd.isna(corr_temp) else "N/A"
            corr_precip_str = f"{corr_precip:+.3f}" if not pd.isna(corr_precip) else "N/A"
            
            # HTML 카드형 레이아웃으로 변환 출력
            st.markdown(f"""
            <div class="kg">
                <div class="kc" style="border-left: 4px solid {CL['r'] if (not pd.isna(corr_temp) and abs(corr_temp)>=0.4) else CL['d']}">
                    <div class="kl">기온(Temperature) 상관계수</div>
                    <div class="kv">{corr_temp_str}</div>
                    <div class="ku">분석 결과: <b>{c_t_label}</b></div>
                </div>
                <div class="kc" style="border-left: 4px solid {CL['o'] if (not pd.isna(corr_precip) and abs(corr_precip)>=0.4) else CL['d']}">
                    <div class="kl">강수량(Precipitation) 상관계수</div>
                    <div class="kv">{corr_precip_str}</div>
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

def get_db_active_countries():
    """
    현재 DB에 등록된 지점들의 국가 코드를 매핑하여 반환합니다.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT region_code FROM regions")
        codes = [row["region_code"] for row in cursor.fetchall()]
    except Exception:
        codes = []
    finally:
        conn.close()
        
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
            
    return sorted(list(countries))

def main():
    st.sidebar.title("SCM 관제 시스템 메뉴")
    menu = st.sidebar.radio("이동", ["메인 대시보드", "지역별 SCM 관제 센터", "등록 지점 리스크 관제"])
    
    if menu == "메인 대시보드":
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
        
        # 실제 DB 기반 통합 메인 대시보드 렌더링
        st.markdown("---")
        render_home_dashboard()
        
    elif menu == "지역별 SCM 관제 센터":
        render_regional_dashboard()
        
    elif menu == "등록 지점 리스크 관제":
        st.markdown(f'<div class="hdr"><div><div class="hdr-t">등록 지점 리스크 관제탑</div><div class="hdr-s">Registered Regions Risk Control Tower &nbsp;·&nbsp; 등록 지점 소속 국가의 실시간 거동 및 물류 영향 분석</div></div></div>', unsafe_allow_html=True)
        
        db_countries = get_db_active_countries()
        wmo_master_df = load_wmo_master()
        
        col_sel1, col_sel2 = st.columns(2)
        
        # 만약 DB에 등록된 국가가 없다면 South Korea를 기본으로 보여주며 안내함
        if not db_countries:
            st.warning("💡 **[안내]** 현재 데이터베이스에 등록된 활성 해외 지점이 없습니다. 기본 관제 국가(South Korea)로 작동합니다.")
            display_countries = ["South Korea"]
        else:
            display_countries = db_countries
            
        selected_country = col_sel1.selectbox("관제 대상 국가 (등록 지점 기반)", options=display_countries)
        
        # 선택한 국가가 실제 DB 등록 국가 목록에 속하는지 체크
        is_registered = (selected_country in db_countries) if db_countries else True
        
        filtered_stations = wmo_master_df[wmo_master_df['country'] == selected_country]
        selected_station_name = col_sel2.selectbox(f"{selected_country} 내 허브 거점", options=filtered_stations['station_name'])
        
        matched_station = filtered_stations[filtered_stations['station_name'] == selected_station_name].iloc[0]
        
        st.info(f"**[SCM 제어 시스템]** 관제 타겟 거점: **{matched_station['station_name']} ({selected_country})** | 위치: `{matched_station['latitude']} / {matched_station['longitude']}`")
        
        if not is_registered:
            st.markdown(f"""
            <div class="ep ew" style="margin-top: 15px;">
                <div class="et">⚠️ 미등록 국가 관제 알림</div>
                <div class="eb"><b>{selected_country}</b>에 속한 창고나 지점이 현재 데이터베이스에 등록되지 않았습니다.<br/>
                지역별 SCM 관제 센터 메뉴에서 해당 국가의 지점(지역 코드: 예: KR-11, US-CA 등)을 먼저 등록하고 재고를 업로드하셔야 실시간 비즈니스 맞춤형 의사결정이 지원됩니다.</div>
            </div>
            """, unsafe_allow_html=True)
            
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
        
        # 5. SCM 리스크 파급 효과 예상 화면 구성
        st.markdown(f"### 🚚 {selected_country} 중심 공급망 리스크 파급 예상 분석")
        st.info("💡 **[직관적 공급망 분석]** 본 관제탑은 추상적인 리스크 점수를 걷어내고, SCM 물류에 직접적으로 미치는 파급 효과(조달 지연, 수요 충격, 운임 폭등)를 고대비 카드로 시각화하여 즉시 조치를 취할 수 있도록 지원합니다.")
        
        # 1계층: 3대 핵심 물류 파급 지표 (대형 고대비 카드 구조)
        c_col1, c_col2, c_col3 = st.columns(3)
        
        # 1) 예상 조달 지연일 (LT Delay)
        lt_delay = scm_metrics["lead_time_delay"]
        lt_color = "#f28b82" if lt_delay >= 2.0 else ("#fdd663" if lt_delay >= 0.5 else "#81c995")
        c_col1.markdown(f"""
        <div class="kc" style="border-left: 5px solid {lt_color}; padding: 15px; background: #202124; min-height: 180px; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
                <div class="kl" style="font-size: 13px; color: #9aa0a6;">📦 예상 조달 지연일 (Lead Time Delay)</div>
                <div class="kv" style="color: {lt_color}; font-size: 32px; font-weight: bold; margin-top: 8px;">+{lt_delay:.1f} 일</div>
            </div>
            <div style="font-size: 11px; color: #e8eaed; line-height: 1.4; margin-top: 10px; border-top: 1px solid #3c4043; padding-top: 6px;">
                {scm_metrics["delay_comment"]}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 2) 소비자 수요 충격 예상치 (Demand Shock)
        ds = scm_metrics["demand_shock_index"]
        ds_color = "#f28b82" if ds <= -10.0 else ("#fdd663" if ds <= -2.0 else "#81c995")
        ds_sign = "+" if ds >= 0 else ""
        c_col2.markdown(f"""
        <div class="kc" style="border-left: 5px solid {ds_color}; padding: 15px; background: #202124; min-height: 180px; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
                <div class="kl" style="font-size: 13px; color: #9aa0a6;">📉 소비자 수요 충격 (Demand Shock)</div>
                <div class="kv" style="color: {ds_color}; font-size: 32px; font-weight: bold; margin-top: 8px;">{ds_sign}{ds:.1f}%</div>
            </div>
            <div style="font-size: 11px; color: #e8eaed; line-height: 1.4; margin-top: 10px; border-top: 1px solid #3c4043; padding-top: 6px;">
                {scm_metrics["demand_comment"]}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 3) 예상 물류 운임 변동률 (Freight Rate Change)
        cf = scm_metrics["freight_rate_change"]
        cf_color = "#f28b82" if cf >= 15.0 else ("#fdd663" if cf >= 5.0 else "#81c995")
        cf_sign = "+" if cf >= 0 else ""
        c_col3.markdown(f"""
        <div class="kc" style="border-left: 5px solid {cf_color}; padding: 15px; background: #202124; min-height: 180px; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
                <div class="kl" style="font-size: 13px; color: #9aa0a6;">🚛 예상 물류 운임 변동률 (Freight Impact)</div>
                <div class="kv" style="color: {cf_color}; font-size: 32px; font-weight: bold; margin-top: 8px;">{cf_sign}{cf:.1f}%</div>
            </div>
            <div style="font-size: 11px; color: #e8eaed; line-height: 1.4; margin-top: 10px; border-top: 1px solid #3c4043; padding-top: 6px;">
                {scm_metrics["freight_comment"]}
            </div>
        </div>
        """, unsafe_allow_html=True)
 
        st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)
        
        # 2계층: 추상적인 수학 연산 모델 점수를 Expander 안으로 격리
        with st.expander("📊 SCM 의사결정 수학적 리스크 분석 엔진 상세 산출 근거"):
            e_col1, e_col2, e_col3 = st.columns(3)
            
            # SCM 종합 리스크 스코어
            r_score = scm_metrics["integrated_risk_score"]
            r_level = "심각 (CRITICAL)" if r_score >= 70 else ("경고 (WARNING)" if r_score >= 40 else "정상 (NORMAL)")
            r_color = "#f28b82" if r_score >= 70 else ("#fdd663" if r_score >= 40 else "#81c995")
            e_col1.markdown(f"""
            <div class="kc" style="border-left: 5px solid {r_color}; padding: 10px; background: #2b2c2f;">
                <div class="kl" style="font-size: 11px;">SCM 종합 리스크 스코어</div>
                <div class="kv" style="color: {r_color}; font-size: 20px; font-weight: bold;">{r_score} / 100</div>
                <div class="ku" style="font-size: 9px; margin-top: 3px;">지수 형태 시그모이드 매핑</div>
            </div>
            """, unsafe_allow_html=True)
            
            # 지정학적 사회적 리스크
            social_risk = scm_metrics["social_score"]
            social_color = "#f28b82" if social_risk >= 50.0 else ("#fdd663" if social_risk >= 20.0 else "#81c995")
            e_col2.markdown(f"""
            <div class="kc" style="border-left: 5px solid {social_color}; padding: 10px; background: #2b2c2f;">
                <div class="kl" style="font-size: 11px;">지정학적/사회 트렌드 리스크</div>
                <div class="kv" style="color: {social_color}; font-size: 20px; font-weight: bold;">{social_risk:.1f} 점</div>
                <div class="ku" style="font-size: 9px; margin-top: 3px;">GDELT ({gdelt_risk_level}) 및 구글 트렌드 융합</div>
            </div>
            """, unsafe_allow_html=True)
            
            # 실시간 날씨 파싱 점수
            w_score = scm_metrics["weather_score"]
            w_color = "#f28b82" if w_score >= 8.0 else ("#fdd663" if w_score >= 4.0 else "#81c995")
            e_col3.markdown(f"""
            <div class="kc" style="border-left: 5px solid {w_color}; padding: 10px; background: #2b2c2f;">
                <div class="kl" style="font-size: 11px;">실시간 날씨 파싱 스코어</div>
                <div class="kv" style="color: {w_color}; font-size: 20px; font-weight: bold;">{w_score:.1f} 점</div>
                <div class="ku" style="font-size: 9px; margin-top: 3px;">허브 날씨 자연어 분석 점수</div>
            </div>
            """, unsafe_allow_html=True)
 
        # GDELT 미디어 헤드라인 요약 노출
        if gdelt_headline and gdelt_headline != "No critical event":
            st.warning(f"🚨 **[지정학적 리스크 헤드라인 실시간 감지]** {gdelt_headline} (GDELT Sentiment Tone: {gdelt_tone})")

def get_db_active_countries():
    """
    현재 DB에 등록된 지점들의 국가 코드를 매핑하여 반환합니다.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT region_code FROM regions")
        codes = [row["region_code"] for row in cursor.fetchall()]
    except Exception:
        codes = []
    finally:
        conn.close()
        
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
            
    return sorted(list(countries))

def main():
    st.sidebar.title("SCM 관제 시스템 메뉴")
    menu = st.sidebar.radio("이동", ["메인 대시보드", "지역별 SCM 관제 센터", "등록 지점 리스크 관제"])
    
    if menu == "메인 대시보드":
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
        
        # 실제 DB 기반 통합 메인 대시보드 렌더링
        st.markdown("---")
        render_home_dashboard()
        
    elif menu == "지역별 SCM 관제 센터":
        render_regional_dashboard()
        
    elif menu == "등록 지점 리스크 관제":
        st.markdown(f'<div class="hdr"><div><div class="hdr-t">등록 지점 리스크 관제탑</div><div class="hdr-s">Registered Regions Risk Control Tower &nbsp;·&nbsp; 등록 지점 소속 국가의 실시간 거동 및 물류 영향 분석</div></div></div>', unsafe_allow_html=True)
        
        db_countries = get_db_active_countries()
        wmo_master_df = load_wmo_master()
        
        col_sel1, col_sel2 = st.columns(2)
        
        # 만약 DB에 등록된 국가가 없다면 South Korea를 기본으로 보여주며 안내함
        if not db_countries:
            st.warning("💡 **[안내]** 현재 데이터베이스에 등록된 활성 해외 지점이 없습니다. 기본 관제 국가(South Korea)로 작동합니다.")
            display_countries = ["South Korea"]
        else:
            display_countries = db_countries
            
        selected_country = col_sel1.selectbox("관제 대상 국가 (등록 지점 기반)", options=display_countries)
        
        # 선택한 국가가 실제 DB 등록 국가 목록에 속하는지 체크
        is_registered = (selected_country in db_countries) if db_countries else True
        
        filtered_stations = wmo_master_df[wmo_master_df['country'] == selected_country]
        selected_station_name = col_sel2.selectbox(f"{selected_country} 내 허브 거점", options=filtered_stations['station_name'])
        
        matched_station = filtered_stations[filtered_stations['station_name'] == selected_station_name].iloc[0]
        
        st.info(f"**[SCM 제어 시스템]** 관제 타겟 거점: **{matched_station['station_name']} ({selected_country})** | 위치: `{matched_station['latitude']} / {matched_station['longitude']}`")
        
        if not is_registered:
            st.markdown(f"""
            <div class="ep ew" style="margin-top: 15px;">
                <div class="et">⚠️ 미등록 국가 관제 알림</div>
                <div class="eb"><b>{selected_country}</b>에 속한 창고나 지점이 현재 데이터베이스에 등록되지 않았습니다.<br/>
                지역별 SCM 관제 센터 메뉴에서 해당 국가의 지점(지역 코드: 예: KR-11, US-CA 등)을 먼저 등록하고 재고를 업로드하셔야 실시간 비즈니스 맞춤형 의사결정이 지원됩니다.</div>
            </div>
            """, unsafe_allow_html=True)
            
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
        
        # 5. SCM 리스크 파급 효과 예상 화면 구성
        st.markdown(f"### 🚚 {selected_country} 중심 공급망 리스크 파급 예상 분석")
        st.info("💡 **[직관적 공급망 분석]** 본 관제탑은 추상적인 리스크 점수를 걷어내고, SCM 물류에 직접적으로 미치는 파급 효과(조달 지연, 수요 충격, 운임 폭등)를 고대비 카드로 시각화하여 즉시 조치를 취할 수 있도록 지원합니다.")
        
        # 1계층: 3대 핵심 물류 파급 지표 (대형 고대비 카드 구조)
        c_col1, c_col2, c_col3 = st.columns(3)
        
        # 1) 예상 조달 지연일 (LT Delay)
        lt_delay = scm_metrics["lead_time_delay"]
        lt_color = "#f28b82" if lt_delay >= 2.0 else ("#fdd663" if lt_delay >= 0.5 else "#81c995")
        c_col1.markdown(f"""
        <div class="kc" style="border-left: 5px solid {lt_color}; padding: 15px; background: #202124; min-height: 180px; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
                <div class="kl" style="font-size: 13px; color: #9aa0a6;">📦 예상 조달 지연일 (Lead Time Delay)</div>
                <div class="kv" style="color: {lt_color}; font-size: 32px; font-weight: bold; margin-top: 8px;">+{lt_delay:.1f} 일</div>
            </div>
            <div style="font-size: 11px; color: #e8eaed; line-height: 1.4; margin-top: 10px; border-top: 1px solid #3c4043; padding-top: 6px;">
                {scm_metrics["delay_comment"]}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 2) 소비자 수요 충격 예상치 (Demand Shock)
        ds = scm_metrics["demand_shock_index"]
        ds_color = "#f28b82" if ds <= -10.0 else ("#fdd663" if ds <= -2.0 else "#81c995")
        ds_sign = "+" if ds >= 0 else ""
        c_col2.markdown(f"""
        <div class="kc" style="border-left: 5px solid {ds_color}; padding: 15px; background: #202124; min-height: 180px; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
                <div class="kl" style="font-size: 13px; color: #9aa0a6;">📉 소비자 수요 충격 (Demand Shock)</div>
                <div class="kv" style="color: {ds_color}; font-size: 32px; font-weight: bold; margin-top: 8px;">{ds_sign}{ds:.1f}%</div>
            </div>
            <div style="font-size: 11px; color: #e8eaed; line-height: 1.4; margin-top: 10px; border-top: 1px solid #3c4043; padding-top: 6px;">
                {scm_metrics["demand_comment"]}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 3) 예상 물류 운임 변동률 (Freight Rate Change)
        cf = scm_metrics["freight_rate_change"]
        cf_color = "#f28b82" if cf >= 15.0 else ("#fdd663" if cf >= 5.0 else "#81c995")
        cf_sign = "+" if cf >= 0 else ""
        c_col3.markdown(f"""
        <div class="kc" style="border-left: 5px solid {cf_color}; padding: 15px; background: #202124; min-height: 180px; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
                <div class="kl" style="font-size: 13px; color: #9aa0a6;">🚛 예상 물류 운임 변동률 (Freight Impact)</div>
                <div class="kv" style="color: {cf_color}; font-size: 32px; font-weight: bold; margin-top: 8px;">{cf_sign}{cf:.1f}%</div>
            </div>
            <div style="font-size: 11px; color: #e8eaed; line-height: 1.4; margin-top: 10px; border-top: 1px solid #3c4043; padding-top: 6px;">
                {scm_metrics["freight_comment"]}
            </div>
        </div>
        """, unsafe_allow_html=True)
 
        st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)
        
        # 2계층: 추상적인 수학 연산 모델 점수를 Expander 안으로 격리
        with st.expander("📊 SCM 의사결정 수학적 리스크 분석 엔진 상세 산출 근거"):
            e_col1, e_col2, e_col3 = st.columns(3)
            
            # SCM 종합 리스크 스코어
            r_score = scm_metrics["integrated_risk_score"]
            r_level = "심각 (CRITICAL)" if r_score >= 70 else ("경고 (WARNING)" if r_score >= 40 else "정상 (NORMAL)")
            r_color = "#f28b82" if r_score >= 70 else ("#fdd663" if r_score >= 40 else "#81c995")
            e_col1.markdown(f"""
            <div class="kc" style="border-left: 5px solid {r_color}; padding: 10px; background: #2b2c2f;">
                <div class="kl" style="font-size: 11px;">SCM 종합 리스크 스코어</div>
                <div class="kv" style="color: {r_color}; font-size: 20px; font-weight: bold;">{r_score} / 100</div>
                <div class="ku" style="font-size: 9px; margin-top: 3px;">지수 형태 시그모이드 매핑</div>
            </div>
            """, unsafe_allow_html=True)
            
            # 지정학적 사회적 리스크
            social_risk = scm_metrics["social_score"]
            social_color = "#f28b82" if social_risk >= 50.0 else ("#fdd663" if social_risk >= 20.0 else "#81c995")
            e_col2.markdown(f"""
            <div class="kc" style="border-left: 5px solid {social_color}; padding: 10px; background: #2b2c2f;">
                <div class="kl" style="font-size: 11px;">지정학적/사회 트렌드 리스크</div>
                <div class="kv" style="color: {social_color}; font-size: 20px; font-weight: bold;">{social_risk:.1f} 점</div>
                <div class="ku" style="font-size: 9px; margin-top: 3px;">GDELT ({gdelt_risk_level}) 및 구글 트렌드 융합</div>
            </div>
            """, unsafe_allow_html=True)
            
            # 실시간 날씨 파싱 점수
            w_score = scm_metrics["weather_score"]
            w_color = "#f28b82" if w_score >= 8.0 else ("#fdd663" if w_score >= 4.0 else "#81c995")
            e_col3.markdown(f"""
            <div class="kc" style="border-left: 5px solid {w_color}; padding: 10px; background: #2b2c2f;">
                <div class="kl" style="font-size: 11px;">실시간 날씨 파싱 스코어</div>
                <div class="kv" style="color: {w_color}; font-size: 20px; font-weight: bold;">{w_score:.1f} 점</div>
                <div class="ku" style="font-size: 9px; margin-top: 3px;">허브 날씨 자연어 분석 점수</div>
            </div>
            """, unsafe_allow_html=True)
 
        # GDELT 미디어 헤드라인 요약 노출
        if gdelt_headline and gdelt_headline != "No critical event":
            st.warning(f"🚨 **[지정학적 리스크 헤드라인 실시간 감지]** {gdelt_headline} (GDELT Sentiment Tone: {gdelt_tone})")


        if fallback_mode:
            pass
        else:
            pass

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
        

        

        
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        
        # GDELT 미디어 헤드라인 요약 노출
        if False:
            pass

if __name__ == "__main__":
    main()
