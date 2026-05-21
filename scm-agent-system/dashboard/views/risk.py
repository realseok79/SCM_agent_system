# dashboard/views/risk.py
import streamlit as st
import auth_helper

def show():
    # CSS 스타일 주입
    st.markdown("""
    <style>
    .stApp{background:#202124;color:#e8eaed}
    .block-container, 
    [data-testid="stMainBlockContainer"], 
    [data-testid="stAppViewBlockContainer"] {
        padding: 0 1.5rem 0 1.5rem !important;
        max-width: 98% !important;
        width: 98% !important;
    }
    .hdr{background:#292a2d;border-bottom:1px solid #3c4043;padding:16px 16px 10px 16px;margin:0 -1.5rem 0.6rem !important;}
    .hdr-t{font-size:16px;font-weight:600;color:#e8eaed}
    .hdr-s{font-size:11px;color:#9aa0a6;margin-top:2px}
    .ep{border-radius:6px;padding:8px 12px;margin-bottom:4px;border-left:3px solid}
    .kb{display:inline-block;font-size:8px;border-radius:3px;padding:1px 5px;margin-top:3px;border:1px solid}
    .kb.ok{background:#81c99511;color:#81c995;border-color:#81c99533}
    .kb.w{background:#f28b8211;color:#f28b82;border-color:#f28b8233}
    </style>
    """, unsafe_allow_html=True)

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
            
            action_plan_html = ""
            action_plan = risk.get("actionPlan")
            if action_plan:
                if action_plan.startswith("[AI Generation]"):
                    lbl = "AI Generation"
                    msg = action_plan.replace("[AI Generation]", "").strip()
                    badge_class = "ok"
                elif action_plan.startswith("[Rule Engine]"):
                    lbl = "Rule Engine"
                    msg = action_plan.replace("[Rule Engine]", "").strip()
                    badge_class = "w"
                else:
                    lbl = "Rule Engine"
                    msg = action_plan
                    badge_class = "w"
                
                action_plan_html = f"""
                <div style="margin-top: 8px; padding-top: 6px; border-top: 1px dashed #3c4043; display: flex; flex-direction: column; gap: 4px;">
                    <div style="display: flex; align-items: center; gap: 6px;">
                        <span style="font-size: 9px; font-weight: 600; color: #9aa0a6; text-transform: uppercase; letter-spacing: .02em;">지점 최적 처방 의견</span>
                        <span class="kb {badge_class}" style="margin-top:0px; font-size: 8px; padding: 1px 4px;">{lbl}</span>
                    </div>
                    <div style="font-size: 11px; color: #e8eaed; line-height: 1.4;">{msg}</div>
                </div>
                """
            
            st.markdown(f"""
            <div class="ep" style="border-left-color: {color}; background-color: {bg_color}; padding: 12px; margin-bottom: 8px;">
                <div class="et" style="color: {color}; font-weight: bold;">📍 {r['regionName']} ({code}) - Risk Level: {level}</div>
                <div class="eb" style="color: #e8eaed; font-size: 12px; margin-top: 4px;">
                    위험도 지수: <b>{risk.get('riskScore'):.1f} 점</b> <br/>
                    상세 상태: {risk.get('description')}
                    {action_plan_html}
                </div>
            </div>
            """, unsafe_allow_html=True)

if __name__ == "__main__":
    show()
