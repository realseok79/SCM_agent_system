# dashboard/pages/risk.py
import streamlit as st
import auth_helper

def render_risk_dashboard():
    st.markdown(f'<div class="hdr"><div><div class="hdr-t">등록 지점 리스크 관제 (Spring AI + 서킷 브레이커)</div><div class="hdr-s">기상 정보와 리스크 스코어를 종합해 실시간 운송 지연 여부를 판정합니다.</div></div></div>', unsafe_allow_html=True)

    regions = auth_helper.api_get("/api/regions")
    if not regions:
        st.warning("⚠️ 분석할 등록 지점이 없습니다.")
        return

    for r in regions:
        code = r["regionCode"]
        risk = auth_helper.api_get(f"/api/dashboard/region/{code}/risk-score")
        if risk:
            level = risk.get("riskLevel", "LOW")
            color = "#f28b82" if level == "HIGH" else "#81c995"
            bg_color = "#f28b820f" if level == "HIGH" else "#81c9950f"
            
            insight = auth_helper.api_get(f"/api/dashboard/region/{code}/insight")
            insight_msg = f"<br/><b>🤖 LLM 최적 처방 (XAI):</b> {insight.get('actionPlanMsg')}" if insight and insight.get('actionPlanMsg') else ""

            import re
            desc_text = risk.get('description', '')
            
            iot_health_val = None
            port_congestion_val = None
            
            # Extract scores using regex
            iot_match = re.search(r"건강도:\s*([0-9.]+)\s*점", desc_text)
            if iot_match:
                try:
                    iot_health_val = float(iot_match.group(1))
                except ValueError:
                    pass
                    
            port_match = re.search(r"항만 혼잡도\s*(?:상승)?\s*\(?\s*([0-9.]+)\s*점\s*\)?", desc_text)
            if port_match:
                try:
                    port_congestion_val = float(port_match.group(1))
                except ValueError:
                    pass

            st.markdown(f"""
            <div class="ep" style="border-left-color: {color}; background-color: {bg_color}; padding: 12px; margin-bottom: 8px;">
                <div class="et" style="color: {color}; font-weight: bold;">📍 {r['regionName']} ({code}) - Risk Level: {level}</div>
                <div class="eb" style="color: #e8eaed; font-size: 12px; margin-top: 4px; margin-bottom: 10px;">
                    위험도 지수: <b>{risk.get('riskScore'):.1f} 점</b> <br/>
                    상세 상태: {risk.get('description')}{insight_msg}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Styled Metric Cards for IoT and Port Congestion
            col_iot, col_port = st.columns(2)
            with col_iot:
                if iot_health_val is not None:
                    status_color = "🔴" if iot_health_val < 80.0 else "🟢"
                    st.markdown(f"""
                    <div style='background-color:#111827; border: 1px solid #374151; padding:10px 14px; border-radius:6px; margin-bottom:15px;'>
                        <div style='font-size:11px; color:#9ca3af;'>📡 창고 IoT 센서 건강도</div>
                        <div style='font-size:16px; font-weight:bold; color:#f3f4f6; margin-top:4px;'>{status_color} {iot_health_val:.1f} 점</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div style='background-color:#111827; border: 1px solid #374151; padding:10px 14px; border-radius:6px; margin-bottom:15px;'>
                        <div style='font-size:11px; color:#9ca3af;'>📡 창고 IoT 센서 건강도</div>
                        <div style='font-size:16px; font-weight:bold; color:#9ca3af; margin-top:4px;'>⚪ 미연동 (Off-line)</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
            with col_port:
                if port_congestion_val is not None:
                    status_color = "🔴" if port_congestion_val > 50.0 else ("🟡" if port_congestion_val > 25.0 else "🟢")
                    st.markdown(f"""
                    <div style='background-color:#111827; border: 1px solid #374151; padding:10px 14px; border-radius:6px; margin-bottom:15px;'>
                        <div style='font-size:11px; color:#9ca3af;'>🚢 해역 항만 혼잡도</div>
                        <div style='font-size:16px; font-weight:bold; color:#f3f4f6; margin-top:4px;'>{status_color} {port_congestion_val:.1f} 점</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div style='background-color:#111827; border: 1px solid #374151; padding:10px 14px; border-radius:6px; margin-bottom:15px;'>
                        <div style='font-size:11px; color:#9ca3af;'>🚢 해역 항만 혼잡도</div>
                        <div style='font-size:16px; font-weight:bold; color:#9ca3af; margin-top:4px;'>⚪ 미연동 (Off-line)</div>
                    </div>
                    """, unsafe_allow_html=True)
