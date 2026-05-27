# dashboard/components/kpi_cards.py
import streamlit as st

def render_sync_health_card(last_sync: str, health_status: str):
    """
    마지막 데이터 동기화 시간 및 시스템 건강 상태 카드를 렌더링합니다.
    """
    st.markdown(f"""
    <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 20px; background-color: rgba(255,255,255,0.02); border-radius: 8px; margin-bottom: 20px; border: 1px solid #30363d;">
        <div style="color: #8b949e; font-size: 12px; letter-spacing: 0.5px;">마지막 데이터 동기화: {last_sync}</div>
        <div style="font-size: 13px; font-weight: bold; letter-spacing: 0.5px;">{health_status}</div>
    </div>
    """, unsafe_allow_html=True)

def render_emergency_order_count(pending_count: int):
    """
    당장 승인해야 할 긴급 발주 건수 메트릭 카드를 렌더링합니다.
    """
    st.markdown(f"""
    <div style="text-align: center; padding: 40px; margin-bottom: 30px; background: rgba(229, 62, 62, 0.05); border: 1px solid rgba(229, 62, 62, 0.3); border-radius: 8px;">
        <div style="font-size: 16px; color: #ff5c5c; font-weight: 600; margin-bottom: 10px;">당장 승인해야 할 긴급 발주 건수</div>
        <div style="font-size: 56px; font-weight: 800; color: #ff5c5c;">{pending_count}</div>
        <div style="font-size: 13px; color: #a0aec0; margin-top: 10px;">승인되지 않은 긴급 발주 내역입니다.</div>
    </div>
    """, unsafe_allow_html=True)
