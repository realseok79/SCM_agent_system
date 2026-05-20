# dashboard/app.py
import streamlit as st
from components.styles import inject_custom_css
from components.auth import render_login_page
from pages.home import render_home_dashboard
from pages.regional import render_regional_dashboard
from pages.risk import render_risk_dashboard
import auth_helper

st.set_page_config(page_title="SCM Agent Control Tower", page_icon="SCM", layout="wide", initial_sidebar_state="expanded")

# Inject general SCM dark styling
inject_custom_css()

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
