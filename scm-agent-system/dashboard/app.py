# dashboard/app.py
import sys
import os
# Add project root to sys.path to enable smooth imports of 'agents' and 'utils' from any run path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import auth_helper

st.set_page_config(page_title="SCM Agent Control Tower", page_icon="SCM", layout="wide", initial_sidebar_state="expanded")

# 공통 CSS 주입 (애플리케이션 전반에 걸쳐 미려한 다크 모드 및 글래스모피즘 효과 적용)
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

# 1. 뷰 컴포넌트 st.Page 객체 정의
login_page = st.Page(render_login_page, title="로그인", icon="🔒")
overview_page = st.Page("dashboard/views/overview.py", title="종합 관제 뷰", icon="📊", default=True)
regional_page = st.Page("dashboard/views/regional.py", title="지역별 SCM 관제 센터", icon="🌐")
forecasting_page = st.Page("dashboard/views/forecasting.py", title="수요 예측 및 출고 분석", icon="📈")
comparison_page = st.Page("dashboard/views/comparison.py", title="자본 효율성 시뮬레이션", icon="💰")
risk_page = st.Page("dashboard/views/risk.py", title="등록 지점 리스크 관제", icon="⚠️")

# 2. 로그인 여부에 따른 내비게이션 라우팅 허브
if "access_token" not in st.session_state:
    pg = st.navigation([login_page], position="hidden")
else:
    pages = {
        "관제 대시보드": [
            overview_page,
            regional_page,
            risk_page,
        ],
        "비즈니스 분석": [
            forecasting_page,
            comparison_page,
        ]
    }
    pg = st.navigation(pages)

    # 로그인 세션 정보 및 로그아웃 버튼 사이드바 렌더링
    st.sidebar.title("SCM 관제탑")
    st.sidebar.write(f"접속 권한: {st.session_state.get('user_role', 'ROLE_USER')}")
    if st.sidebar.button("로그아웃"):
        auth_helper.api_logout()
        st.rerun()

# 3. 뷰 컴포넌트 실행
pg.run()
