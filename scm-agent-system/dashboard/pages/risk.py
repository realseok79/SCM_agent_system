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
            
            st.markdown(f"""
            <div class="ep" style="border-left-color: {color}; background-color: {bg_color}; padding: 12px; margin-bottom: 8px;">
                <div class="et" style="color: {color}; font-weight: bold;">📍 {r['regionName']} ({code}) - Risk Level: {level}</div>
                <div class="eb" style="color: #e8eaed; font-size: 12px; margin-top: 4px;">
                    위험도 지수: <b>{risk.get('riskScore'):.1f} 점</b> <br/>
                    상세 상태: {risk.get('description')}
                </div>
            </div>
            """, unsafe_allow_html=True)
