# dashboard/app.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import time
import requests
from datetime import datetime
from matplotlib import rc
import auth_helper

# Matplotlib 한글 폰트 설정
plt.rcParams["axes.unicode_minus"] = False
for f in ["AppleGothic", "NanumGothic", "Malgun Gothic"]:
    try:
        rc("font", family=f)
        break
    except:
        continue

BG = '#202124'
TX = '#e8eaed'

def sax(ax):
    ax.tick_params(colors=TX, labelsize=7)
    for spine in ax.spines.values():
        spine.set_color('#3c4043')
    ax.yaxis.grid(True, color="#3c4043", alpha=0.5, ls=":")
    ax.xaxis.grid(False)

st.set_page_config(page_title="SCM Agent Control Tower", page_icon="SCM", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
.stApp{background:#202124;color:#e8eaed}
.block-container, 
[data-testid="stMainBlockContainer"], 
[data-testid="stAppViewBlockContainer"] {
    padding: 0 1.5rem 0 1.5rem !important;
    max-width: 98% !important;
    width: 98% !important;
}
.hdr{background:#292a2d;border-bottom:1px solid #3c4043;padding:16px 16px 10px 16px;margin:0 -1.5rem 0.6rem !important;}
.hdr-t{font-size:16px;font-weight:600;color:#e8eaed}
.hdr-s{font-size:11px;color:#9aa0a6;margin-top:2px}
.sec{font-size:11px;font-weight:600;color:#9aa0a6;text-transform:uppercase;letter-spacing:.06em;border-bottom:1px solid #3c4043;padding-bottom:4px;margin:0.8rem 0 0.4rem}
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
.ep{border-radius:6px;padding:8px 12px;margin-bottom:4px;border-left:3px solid}
.ec{background:#f28b8209;border-color:#f28b82}.ew{background:#fdd66309;border-color:#fdd663}.en{background:#81c99509;border-color:#81c995}
.et{font-size:11px;font-weight:500;margin-bottom:3px}.eb{font-size:10px;color:#9aa0a6;line-height:1.5}
</style>
""", unsafe_allow_html=True)

def render_login_page():
    st.markdown('<div class="hdr"><div class="hdr-t">Enterprise SCM 자율 관제탑 로그인</div><div class="hdr-s">본 관제 대시보드에 접근하려면 인증이 필요합니다.</div></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        with st.form("login_form"):
            username = st.text_input("Username", "admin")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("관제탑 접속")
            if submitted:
                success, msg = auth_helper.api_login(username, password)
                if success:
                    st.success("인증에 성공했습니다. 로딩 중...")
                    st.rerun()
                else:
                    st.error(msg)

def render_home_dashboard():
    summary = auth_helper.api_get("/api/dashboard/summary")
    if not summary:
        st.warning("⚠️ 백엔드 서비스와 통신할 수 없거나 세션이 만료되었습니다. 로그인 상태를 확인해 주세요.")
        return

    st.markdown(f'<div class="hdr"><div><div class="hdr-t">SCM AI 자율 제어 관제탑 (REST Dashboard)</div><div class="hdr-s">스프링 백엔드 통합 SCM 텔레메트리 &nbsp;·&nbsp; {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div></div></div>', unsafe_allow_html=True)

    # KPI 융합 카드 렌더링
    st.markdown(f'''<div class="kg">
<div class="kc"><div class="kl">등록 지점 수</div><div class="kv b">{summary.get("totalRegions", 0)} 개소</div><div class="ku">실무 가용 물류 거점</div></div>
<div class="kc"><div class="kl">전체 모니터링 SKU</div><div class="kv">12 품목</div><div class="ku">등록된 활성 상품 종류</div></div>
<div class="kc"><div class="kl">통합 가용 재고량</div><div class="kv g">{summary.get("totalStock", 0.0):,.0f} 개</div><div class="ku">지점별 최신 재고 합산</div></div>
<div class="kc"><div class="kl">발주 장애 사고 건수</div><div class="kv r">{summary.get("totalStockOutIncidents", 0)} 건</div><div class="ku">안전 기준 미달 품절 사고</div></div>
<div class="kc"><div class="kl">관제 시스템 상태</div><div class="kv g">{summary.get("systemStatus", "STABLE")}</div><div class="ku">서버 정상 작동 유무</div><div class="kb ok">정상</div></div>
</div>''', unsafe_allow_html=True)

    # SCM 운영 및 발주 체크리스트 추가
    st.markdown("### 📋 오늘의 SCM 운영 및 발주 체크리스트")
    chk_col1, chk_col2 = st.columns([1.8, 1.2])

    with chk_col1:
        st.markdown('<div class="cc"><div class="ct"><span class="dt" style="background:#f28b82"></span>자동 발주 승인 대기 목록</div>', unsafe_allow_html=True)
        if "order_approved_seoul" not in st.session_state:
            st.session_state["order_approved_seoul"] = False

        if not st.session_state["order_approved_seoul"]:
            st.markdown("""
            <div class="ep ec" style="border-left-color: #f28b82; padding: 12px; margin-bottom: 10px;">
                <div class="et" style="color: #f28b82; font-weight: bold; font-size: 13px;">⚠️ [안전 재고 경고] 서울 물류창고 마스크 고갈 우려</div>
                <div class="eb" style="font-size: 12px; margin-top: 5px; color: #e8eaed;">
                    서울점 <b>마스크</b> 품목 재고가 안전재고 ROP 이하로 떨어졌습니다.<br/>
                    자율 AI 최적 발주량 <b>500개</b>의 주문을 승인하겠습니까?
                </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button("📥 자동 발주 승인 및 다운로드", key="btn_download_seoul"):
                st.session_state["order_approved_seoul"] = True
                st.success("발주 승인되었습니다.")
                st.rerun()
        else:
            st.markdown("""
            <div class="ep en" style="border-left-color: #81c995; padding: 12px; margin-bottom: 10px;">
                <div class="et" style="color: #81c995; font-weight: bold; font-size: 13px;">✅ [발주 완료] 서울점 마스크 발주서 생성 완료</div>
                <div class="eb" style="font-size: 12px; margin-top: 5px; color: #e8eaed;">
                    서울점 <b>마스크 500개</b>에 대한 발주 요청이 승인되어 <b>진행 중</b> 상태로 전환되었습니다.
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("🔄 발주 요청 초기화 (테스트용)", key="reset_seoul"):
                st.session_state["order_approved_seoul"] = False
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with chk_col2:
        st.markdown('<div class="cc"><div class="ct"><span class="dt" style="background:#81c995"></span>실시간 물류 건강 지표</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="ep en" style="border-left-color: #81c995; padding: 12px; min-height: 110px;">
            <div class="et" style="color: #81c995; font-weight: bold; font-size: 13px;">🟢 전 지점 운송 경로 정상</div>
            <div class="eb" style="font-size: 12px; margin-top: 5px; color: #e8eaed;">
                현재 모든 물류 거점의 환경이 양호합니다.<br/>
                배송 지연 요인이 식별되지 않았습니다.
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # 최근 7일 재고 추이 시각화
    st.markdown('<div class="cc"><div class="ct"><span class="dt" style="background:#8ab4f8"></span>최근 7일간 전체 재고 추이 (REST 집계)</div>', unsafe_allow_html=True)
    trend_data = auth_helper.api_get("/api/dashboard/stock-trend")
    if trend_data:
        df = pd.DataFrame(trend_data)
        fig, ax = plt.subplots(figsize=(10, 2.5), dpi=100)
        fig.patch.set_facecolor(BG)
        ax.set_facecolor(BG)
        ax.plot(df["date"], df["quantity"], color="#8ab4f8", lw=1.8, marker="o", label="전체 재고 합계")
        ax.fill_between(df["date"], df["quantity"], alpha=0.08, color="#8ab4f8")
        sax(ax)
        ax.set_xlabel("일자 (Date)", fontsize=8, color=TX)
        ax.set_ylabel("수량 (Units)", fontsize=8, color=TX)
        ax.legend(fontsize=7, framealpha=0, loc="upper left", labelcolor=TX)
        fig.tight_layout(pad=0.5)
        st.pyplot(fig, use_container_width=True)
    else:
        st.info("💡 차트를 그리기 위한 데이터가 부족합니다.")
    st.markdown('</div>', unsafe_allow_html=True)

def render_regional_dashboard():
    st.markdown(f'<div class="hdr"><div><div class="hdr-t">지역별 SCM 관제 센터 (REST 연동)</div><div class="hdr-s">지역별 재고 CRUD 및 기상 융합 인공지능 분석 관제탑</div></div></div>', unsafe_allow_html=True)

    # 지역 조회
    regions = auth_helper.api_get("/api/regions")
    if regions is None:
        st.warning("⚠️ 지역 정보를 읽어오지 못했습니다.")
        return

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
                        payload = {
                            "regionName": new_name,
                            "regionCode": new_name, // standardizer가 변환함
                            "description": new_desc
                        }
                        res = auth_helper.api_post("/api/regions", payload)
                        if res:
                            st.success("지역이 성공적으로 등록되었습니다.")
                            st.rerun()
                        else:
                            st.error("지역 등록 실패")

        if not regions:
            st.warning("⚠️ 등록된 지역이 없습니다. 먼저 지역을 등록해 주세요.")
            return

        region_options = {f"{r['regionName']} ({r['regionCode']})": r for r in regions}
        selected_key = st.selectbox("관제할 지역 선택", options=list(region_options.keys()))
        selected_region = region_options[selected_key]

        st.markdown(f"""
        <div class="kc" style="margin-bottom: 10px;">
            <div class="kl">선택된 지역 코드</div>
            <div class="kv b">{selected_region['regionCode']}</div>
            <div class="ku">{selected_region['description'] or '설명 없음'}</div>
        </div>
        """, unsafe_allow_html=True)

        # 데이터 업로드
        st.markdown('<div class="sec">SCM 엑셀/CSV 데이터 업로드</div>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader("지역 재고 및 수요 이력 업로드", type=["csv", "xlsx", "xls"], key="regional_uploader")
        
        if uploaded_file is not None:
            if st.button("🚀 데이터 파싱 및 라우팅 실행", key="btn_regional_route"):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                data = {"company_id": "COMPANY_SIGMA"}
                headers = {"Authorization": f"Bearer {st.session_state['access_token']}"}
                try:
                    res = requests.post(f"{auth_helper.API_BASE_URL}/api/regions/upload", data=data, files=files, headers=headers, timeout=15)
                    if res.status_code == 200:
                        st.success("데이터 업로드 및 파싱이 완료되었습니다.")
                        st.json(res.json())
                    else:
                        st.error(f"파싱 실패: {res.text}")
                except Exception as e:
                    st.error(f"파싱 중 연결 실패: {e}")

    with col2:
        st.markdown('<div class="sec">실시간 지역 재고 흐름 & 기상 융합 분석</div>', unsafe_allow_html=True)

        # 1. 해당 지역 재고 데이터 조회
        inv_data = auth_helper.api_get(f"/api/dashboard/region/{selected_region['regionCode']}/inventory")
        if not inv_data:
            st.info("💡 분석을 진행하기 위해 좌측 패널에서 재고 데이터를 업로드해 주세요.")
            return

        inv_df = pd.DataFrame([
            {
                "product_name": inv["id"]["productName"],
                "date": inv["id"]["date"],
                "quantity": inv["quantity"]
            } for inv in inv_data
        ])

        # 2. 기상 데이터 조회
        weather_data = auth_helper.api_get(f"/api/dashboard/region/{selected_region['regionCode']}/weather")
        weather_df = pd.DataFrame(weather_data) if weather_data else pd.DataFrame()

        # 재고 KPI 카드 렌더링
        products = inv_df["product_name"].unique()
        total_qty = inv_df.groupby("product_name")["quantity"].last().sum()

        st.markdown(f'''<div class="kg">
        <div class="kc"><div class="kl">모니터링 품목수</div><div class="kv">{len(products)} SKU</div><div class="ku">지정 품목 리스트</div></div>
        <div class="kc"><div class="kl">최신 총 재고량</div><div class="kv b">{total_qty:,.0f}</div><div class="ku">units (마지막 일자 기준)</div></div>
        <div class="kc"><div class="kl">기상 관측일수</div><div class="kv g">{len(weather_df)}일</div><div class="ku">동기화 완료</div></div>
        </div>''', unsafe_allow_html=True)

        # 품목 선택 필터
        selected_prod = st.selectbox("분석할 품목 선택", options=products)
        prod_inv = inv_df[inv_df["product_name"] == selected_prod]

        # 1. 재고 변동 차트 시각화
        st.markdown(f'<div class="cc"><div class="ct"><span class="dt" style="background:#8ab4f8"></span>[{selected_prod}] 일별 재고 변동 추이</div>', unsafe_allow_html=True)
        
        fig, ax = plt.subplots(figsize=(10, 2.5), dpi=100)
        fig.patch.set_facecolor(BG)
        ax.set_facecolor(BG)
        
        dates_parsed = pd.to_datetime(prod_inv["date"])
        ax.plot(dates_parsed, prod_inv["quantity"], color="#8ab4f8", lw=1.6, label="재고량")
        ax.fill_between(dates_parsed, prod_inv["quantity"], alpha=0.08, color="#8ab4f8")
        
        sax(ax)
        ax.set_xlabel("날짜 (Date)", fontsize=8, color=TX)
        ax.set_ylabel("수량 (Units)", fontsize=8, color=TX)
        fig.tight_layout(pad=0.5)
        st.pyplot(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # 2. 데이터 무결성 검증
        st.markdown('<div class="sec">재고 효율성 및 데이터 무결성 관제탑</div>', unsafe_allow_html=True)
        latest_date = prod_inv["date"].iloc[-1]
        
        # 무결성 검증 API 호출
        integrity_result = auth_helper.api_get(f"/api/dashboard/region/{selected_region['regionCode']}/integrity?product={selected_prod}&date={latest_date}")
        if integrity_result:
            if integrity_result.get("isConsistent", True):
                st.success(f"✅ 데이터 무결성 검증 완료 | {integrity_result.get('message')}")
            else:
                st.error(f"⚠️ 무결성 불일치 발생 | {integrity_result.get('message')}")

def render_risk_dashboard():
    st.markdown(f'<div class="hdr"><div><div class="hdr-t">등록 지점 리스크 관제 (Spring AI + 서킷 브레이커)</div><div class="hdr-s">기상 정보와 리스크 스코어를 종합해 실시간 운송 지연 여부를 판정합니다.</div></div></div>', unsafe_allow_html=True)

    regions = auth_helper.api_get("/api/regions")
    if not regions:
        st.warning("⚠️ 분석할 등록 지점이 없습니다.")
        return

    for r in regions:
        code = r["regionCode"]
        risk = auth_helper.api_get(f"/api/dashboard/region/{code}/risk-score")
        if risk:
            level = risk.get("riskLevel", "LOW")
            color = "#f28b82" if level == "HIGH" else "#81c995"
            bg_color = "#f28b820f" if level == "HIGH" else "#81c9950f"
            
            st.markdown(f"""
            <div class="ep" style="border-left-color: {color}; background-color: {bg_color}; padding: 12px; margin-bottom: 8px;">
                <div class="et" style="color: {color}; font-weight: bold;">📍 {r['regionName']} ({code}) - Risk Level: {level}</div>
                <div class="eb" style="color: #e8eaed; font-size: 12px; margin-top: 4px;">
                    위험도 지수: <b>{risk.get('riskScore'):.1f} 점</b> <br/>
                    상세 상태: {risk.get('description')}
                </div>
            </div>
            """, unsafe_allow_html=True)

def main():
    if "access_token" not in st.session_state:
        render_login_page()
    else:
        st.sidebar.title("SCM 관제탑")
        st.sidebar.write(f"접속 권한: {st.session_state.get('user_role', 'ROLE_USER')}")
        
        menu = st.sidebar.radio("이동", ["메인 대시보드", "지역별 SCM 관제 센터", "등록 지점 리스크 관제"])
        
        if st.sidebar.button("로그아웃"):
            auth_helper.api_logout()
            st.rerun()
            
        if menu == "메인 대시보드":
            render_home_dashboard()
        elif menu == "지역별 SCM 관제 센터":
            render_regional_dashboard()
        elif menu == "등록 지점 리스크 관제":
            render_risk_dashboard()

if __name__ == "__main__":
    main()
