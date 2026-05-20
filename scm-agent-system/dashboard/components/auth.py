# dashboard/components/auth.py
import streamlit as st
import auth_helper

def render_login_page():
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0 1rem 0;">
        <h1 style="font-size: 2.2rem; font-weight: 800; color: #8ab4f8; margin-bottom: 0.5rem; letter-spacing: -0.03em;">
            🛰️ SCM Agent Control Tower
        </h1>
        <p style="color: #9aa0a6; font-size: 0.95rem; margin-bottom: 2rem;">
            지능형 공급망 및 자율 재고 조율 시스템 관제탑
        </p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 1.3, 1])
    with c2:
        st.markdown("""
        <div style="background: #292a2d; border: 1px solid #3c4043; border-radius: 12px; padding: 24px; box-shadow: 0 8px 24px rgba(0,0,0,0.3); margin-bottom: 20px;">
            <div style="font-size: 1.1rem; font-weight: 600; color: #e8eaed; margin-bottom: 15px;">로그인 인증</div>
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
