# dashboard/app.py
import streamlit as st
from components.styles import inject_custom_css
from components.auth import render_login_page
from views.home import render_home_dashboard
from views.regional import render_regional_dashboard
from views.risk import render_risk_dashboard
from views.ai_learning import render_ai_learning_dashboard
from views.iot_management import render_iot_management
from views.audit_log import render_audit_log_dashboard
from views.mlops_simulator import render_mlops_simulator_dashboard
from views.agent_workflow import render_agent_workflow
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
        
        # 🧪 데모 모드 토글
        demo_mode = st.sidebar.checkbox("🧪 데모 시뮬레이션 모드", value=False)
        st.session_state["demo_mode"] = demo_mode
        if demo_mode:
            st.sidebar.info("💡 데모 모드 활성화됨. 하단 대시보드에서 가상 비상 시나리오를 트리거할 수 있습니다.")

        # 🔔 알림 센터 (Notification Center) & Real-time Toasts
        try:
            logs = auth_helper.api_get("/api/audit-logs")
            if logs:
                if "last_seen_audit_id" not in st.session_state:
                    st.session_state["last_seen_audit_id"] = logs[0].get("id", 0)
                else:
                    last_seen = st.session_state["last_seen_audit_id"]
                    new_logs = [l for l in logs if l.get("id", 0) > last_seen]
                    for nl in reversed(new_logs):
                        st.toast(f"🔔 {nl.get('message')}")
                    st.session_state["last_seen_audit_id"] = logs[0].get("id", 0)

                with st.sidebar.expander("🔔 알림 센터 (최근 5건)", expanded=True):
                    for log in logs[:5]:
                        etype = log.get("eventType")
                        msg = log.get("message")
                        prefix = "ℹ️"
                        if etype == "ORDER_APPROVED":
                            prefix = "🟢"
                        elif etype == "ORDER_REJECTED":
                            prefix = "🔴"
                        elif etype == "DEVICE_MAINTENANCE":
                            prefix = "🛠️"
                        elif etype == "DEVICE_ACTIVE":
                            prefix = "📡"
                        elif etype == "RISK_ALERT":
                            prefix = "⚠️"
                        
                        st.markdown(f"<div style='font-size: 11px; margin-bottom: 6px; border-bottom: 1px solid #2d3748; padding-bottom: 4px;'>{prefix} {msg}</div>", unsafe_allow_html=True)
        except Exception as e:
            st.sidebar.error(f"알림 로드 오류: {e}")
        
        # 권한별 메뉴 분기
        MENU_BY_ROLE = {
            "ROLE_ADMIN": ["메인 대시보드", "지역별 SCM 관제 센터", "등록 지점 리스크 관제", "📟 IoT 센서 모니터링", "🤖 자율 발주 워크플로우", "🔄 매핑 피드백 현황", "🤖 MLOps 관제 및 시뮬레이터", "📋 감사 로그"],
            "ROLE_LOGISTICS": ["메인 대시보드", "지역별 SCM 관제 센터", "등록 지점 리스크 관제", "🤖 자율 발주 워크플로우", "🤖 MLOps 관제 및 시뮬레이터"],
            "ROLE_EXECUTIVE": ["메인 대시보드 (경영진)", "🔄 매핑 피드백 현황", "🤖 MLOps 관제 및 시뮬레이터", "📋 감사 로그"]
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
        elif menu == "📟 IoT 센서 모니터링":
            render_iot_management()
        elif menu == "🤖 자율 발주 워크플로우":
            render_agent_workflow()
        elif menu == "🔄 매핑 피드백 현황":
            render_ai_learning_dashboard()
        elif menu == "🤖 MLOps 관제 및 시뮬레이터":
            render_mlops_simulator_dashboard()
        elif menu == "📋 감사 로그":
            render_audit_log_dashboard()


if __name__ == "__main__":
    main()
