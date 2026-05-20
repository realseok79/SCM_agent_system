# dashboard/components/auth.py
import streamlit as st
import auth_helper

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
