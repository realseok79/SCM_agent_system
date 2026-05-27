# dashboard/views/audit_log.py
import streamlit as st
import pandas as pd
import auth_helper

from components.styles import inject_custom_css

def render_audit_log_dashboard():
    inject_custom_css()
    st.markdown(f'<div class="hdr"><div><div class="hdr-t">시스템 감사 로그 (Audit Logs)</div><div class="hdr-s">SCM 시스템의 모든 주요 상태 변화, 자동 재배정 주문 승인/반려 및 장비 작동 기록을 추적합니다.</div></div></div>', unsafe_allow_html=True)

    # Fetch logs
    logs = auth_helper.api_get("/api/audit-logs")
    if not logs:
        st.info("기록된 감사 로그가 존재하지 않습니다.")
        return

    # Filter section
    col_filter_type, col_filter_user = st.columns(2)
    
    event_types = sorted(list(set(l.get("eventType") for l in logs)))
    triggered_by_users = sorted(list(set(l.get("triggeredBy") for l in logs)))
    
    with col_filter_type:
        selected_type = st.selectbox("이벤트 유형 필터", ["전체"] + event_types)
        
    with col_filter_user:
        selected_user = st.selectbox("발생자 필터", ["전체"] + triggered_by_users)

    # Filter logs
    filtered_logs = logs
    if selected_type != "전체":
        filtered_logs = [l for l in filtered_logs if l.get("eventType") == selected_type]
    if selected_user != "전체":
        filtered_logs = [l for l in filtered_logs if l.get("triggeredBy") == selected_user]

    if not filtered_logs:
        st.warning(" 필터 조건에 일치하는 로그가 없습니다.")
        return

    # Render table
    df_data = []
    for l in filtered_logs:
        df_data.append({
            "ID": l.get("id"),
            "이벤트 유형": l.get("eventType"),
            "상세 내용": l.get("message"),
            "발생자": l.get("triggeredBy"),
            "기록 일시": l.get("recordedAt") or "기록 없음"
        })
    df = pd.DataFrame(df_data)
    
    # Render with nice styles
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Detailed card view
    st.markdown('<div class="sec" style="margin-top: 20px;">로그 세부 타임라인</div>', unsafe_allow_html=True)
    
    for l in filtered_logs[:15]:
        etype = l.get("eventType")
        msg = l.get("message")
        tby = l.get("triggeredBy")
        time_str = l.get("recordedAt", "").replace("T", " ")[:19]
        
        prefix = ""
        bg_col = "#2d37480a"
        border_col = "#4a5568"
        
        if etype == "ORDER_APPROVED":
            prefix = ""
            bg_col = "#2f855a0a"
            border_col = "#38a169"
        elif etype == "ORDER_REJECTED":
            prefix = ""
            bg_col = "#9b2c2c0a"
            border_col = "#e53e3e"
        elif etype == "DEVICE_MAINTENANCE":
            prefix = ""
            bg_col = "#d69e2e0a"
            border_col = "#dd6b20"
        elif etype == "DEVICE_ACTIVE":
            prefix = "📡"
            bg_col = "#3182ce0a"
            border_col = "#3182ce"
        elif etype == "RISK_ALERT":
            prefix = ""
            bg_col = "#e53e3e0d"
            border_col = "#e53e3e"

        st.markdown(f"""
        <div style="border-left: 4px solid {border_col}; background-color: {bg_col}; padding: 10px 14px; margin-bottom: 8px; border-radius: 4px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-weight: bold; color: #f7fafc;">{prefix} {etype}</span>
                <span style="font-size: 11px; color: #a0aec0;">{time_str} | {tby}</span>
            </div>
            <div style="font-size: 13px; margin-top: 4px; color: #cbd5e0;">{msg}</div>
        </div>
        """, unsafe_allow_html=True)
