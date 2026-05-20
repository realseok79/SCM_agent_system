# dashboard/app.py
import streamlit as st
from components.styles import inject_custom_css
from components.auth import render_login_page
from views.home import render_home_dashboard
from views.regional import render_regional_dashboard
from views.risk import render_risk_dashboard
from views.ai_learning import render_ai_learning_dashboard
import auth_helper

st.set_page_config(page_title="SCM Agent Control Tower", page_icon="SCM", layout="wide", initial_sidebar_state="expanded")

# Inject general SCM dark styling
inject_custom_css()

def main():
    if "access_token" not in st.session_state:
        render_login_page()
    else:
        st.sidebar.title("SCM 관제탑")
        
        role = st.session_state.get('user_role', 'ROLE_USER')
        st.sidebar.write(f"접속 권한: `{role}`")
        
        # 권한별 메뉴 분기
        MENU_BY_ROLE = {
            "ROLE_ADMIN": ["메인 대시보드", "지역별 SCM 관제 센터", "등록 지점 리스크 관제", "🔄 매핑 피드백 현황"],
            "ROLE_LOGISTICS": ["메인 대시보드", "지역별 SCM 관제 센터", "등록 지점 리스크 관제"],
            "ROLE_EXECUTIVE": ["메인 대시보드 (경영진)", "🔄 매핑 피드백 현황"]
        }
        
        # 기본 fallback으로 ROLE_LOGISTICS 지정
        menu_options = MENU_BY_ROLE.get(role, MENU_BY_ROLE["ROLE_LOGISTICS"])
        menu = st.sidebar.radio("이동", menu_options)
        
        if st.sidebar.button("로그아웃"):
            auth_helper.api_logout()
            st.rerun()
            
        if menu == "메인 대시보드" or menu == "메인 대시보드 (경영진)":
            render_home_dashboard()
        elif menu == "지역별 SCM 관제 센터":
            render_regional_dashboard()
        elif menu == "등록 지점 리스크 관제":
            render_risk_dashboard()
        elif menu == "🔄 매핑 피드백 현황":
            render_ai_learning_dashboard()

if __name__ == "__main__":
    main()
