# dashboard/components/auth.py
import streamlit as st
import auth_helper

def render_login_page():
    st.markdown("""
    <style>
    /* Premium background radial gradient */
    .stApp {
        background: radial-gradient(circle at 50% 50%, #172a45, #0a192f) !important;
    }
    </style>
    <div style="text-align: center; padding: 3rem 0 1rem 0;">
        <h1 style="font-size: 2.5rem; font-weight: 800; color: #64ffda; margin-bottom: 0.5rem; letter-spacing: -0.03em; text-shadow: 0 0 30px rgba(100,255,218,0.25);">
            🛰️ SCM Agent Control Tower
        </h1>
        <p style="color: #8892b0; font-size: 1rem; margin-bottom: 2rem; letter-spacing: 0.02em;">
            지능형 공급망 및 자율 재고 조율 시스템 관제탑
        </p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 1.3, 1])
    with c2:
        st.markdown("""
        <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(100, 255, 218, 0.15); border-radius: 16px; padding: 28px; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); margin-bottom: 20px;">
            <div style="font-size: 1.15rem; font-weight: 700; color: #ccd6f6; margin-bottom: 18px; text-align: center; letter-spacing: 0.08em; text-shadow: 0 0 10px rgba(100,255,218,0.1);">🔒 SECURE ACCESS LOGIN</div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("아이디 (Username)", "admin")
            password = st.text_input("비밀번호 (Password)", type="password")
            submitted = st.form_submit_button("관제탑 접속 시스템 활성화", use_container_width=True)
            
            if submitted:
                success, msg = auth_helper.api_login(username, password)
                if success:
                    st.success("🔒 인증 성공! 관제탑을 로딩 중입니다...")
                    st.rerun()
                else:
                    st.error(f"❌ 로그인 실패: {msg}")
                    
        st.markdown("</div>", unsafe_allow_html=True)
        
        # 사용자를 위한 친절한 계정 권한 가이드라인 추가
        st.info("""
        💡 **테스트용 신속 접속 계정 정보**
        - **최고 관리자 (ROLE_ADMIN)**: `admin` / `admin` (모든 승인, 반려, 지점 제어 가능)
        - **물류 담당자 (ROLE_LOGISTICS)**: `logistics` / `logistics` (발주 승인 및 관제 가능, AI 피드백 제어 불가)
        - **경영진 (ROLE_EXECUTIVE)**: `executive` / `executive` (시뮬레이션 및 현황 리포트 읽기 전용)
        """)
