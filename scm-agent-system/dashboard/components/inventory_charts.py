# dashboard/components/inventory_charts.py
import streamlit as st
import time
import auth_helper

def render_pending_orders_list(pending_orders):
    """
    긴급 발주 대기 목록을 expander 내부에서 렌더링하고 승인 기능을 수행합니다.
    """
    if len(pending_orders) > 0:
        with st.expander("🚨 긴급 발주 대기 목록 확인 및 승인", expanded=True):
            user_role = st.session_state.get("user_role", "ROLE_USER")
            if user_role == "ROLE_EXECUTIVE":
                st.info("경영진 계정은 발주 승인 권한이 없습니다.")
                
            for order in pending_orders:
                order_id = order.get("transferId")
                prod = order.get("productName")
                from_reg = order.get("fromRegion")
                to_reg = order.get("toRegion")
                qty = order.get("transferQty")
                reason = order.get("reason", "안전재고 임계치 미달")
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**[{from_reg} ➔ {to_reg}] {prod} ({qty}개)**  \n사유: {reason}")
                
                with col2:
                    if user_role != "ROLE_EXECUTIVE":
                        if st.button(f"승인", key=f"btn_approve_{order_id}", use_container_width=True, type="primary"):
                            with st.spinner("처리 중..."):
                                auth_helper.api_post(f"/api/orders/{order_id}/approve", {})
                            st.success("승인 완료")
                            time.sleep(0.5)
                            st.rerun()
                st.divider()

def render_high_risk_regions(regions, batch_risks):
    """
    실시간 위험 지점 리스트를 렌더링합니다.
    """
    st.markdown("### ⚠️ 실시간 위험 지점 리스트")
    high_risk_found = False
    if regions:
        for r in regions:
            code = r.get("regionCode")
            region_data = batch_risks.get(code, {})
            risk = region_data.get("risk")
            if risk and risk.get("riskLevel") == "HIGH":
                high_risk_found = True
                score = risk.get("riskScore", 0)
                desc = risk.get("description", "")
                
                st.markdown(f"""
                <div style="border-left: 4px solid #ff5c5c; background-color: rgba(255, 92, 92, 0.05); padding: 15px; border-radius: 6px; margin-bottom: 12px; border: 1px solid #30363d;">
                    <div style="color: #ff5c5c; font-weight: bold; font-size: 14px; margin-bottom: 5px;">
                        🚨 {r.get('regionName')} ({code}) - 위험도: {score:.1f}점
                    </div>
                    <div style="color: #c9d1d9; font-size: 13px;">
                        {desc}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
    if not high_risk_found:
        st.info("현재 위험도 HIGH로 식별된 지점이 없습니다.")
