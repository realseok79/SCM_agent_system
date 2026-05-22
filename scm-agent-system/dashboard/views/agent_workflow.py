# dashboard/views/agent_workflow.py
import streamlit as st
import time
import json
from datetime import datetime
import auth_helper
from components.styles import inject_custom_css, BG, TX

def render_agent_workflow():
    # Inject custom CSS styles
    inject_custom_css()

    st.markdown("""
    <div class="hdr">
        <div>
            <div class="hdr-t">🤖 SCM AI 자율 제어 에이전트 워크플로우</div>
            <div class="hdr-s">각 SCM 에이전트의 Chain-of-Thought (생각 체인) 파이프라인과 자율 의사결정 과정을 시각화합니다.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Fetch regions for the selector
    regions = auth_helper.api_get("/api/regions")
    if not regions:
        regions = [{"regionName": "기본 관제소", "regionCode": "KR-11"}]
    region_options = {f"{r['regionName']} ({r['regionCode']})": r['regionCode'] for r in regions}

    # Initialize session states
    if "sim_running" not in st.session_state:
        st.session_state["sim_running"] = False
    if "sim_completed" not in st.session_state:
        st.session_state["sim_completed"] = False
    if "sim_results" not in st.session_state:
        st.session_state["sim_results"] = {}

    sim_running = st.session_state["sim_running"]
    sim_completed = st.session_state["sim_completed"]

    col_ctrl, col_display = st.columns([1, 1.6])

    with col_ctrl:
        st.markdown('<div class="sec">⚙️ 시뮬레이션 설정 파라미터</div>', unsafe_allow_html=True)
        st.markdown('<div class="cc">', unsafe_allow_html=True)
        
        # Disabled when simulation is running
        selected_sku = st.selectbox(
            "분석 SKU 선택",
            options=["반도체 칩", "마스크", "종합 품목"],
            disabled=sim_running,
            key="sim_sku"
        )
        
        selected_region_lbl = st.selectbox(
            "대상 지점 선택",
            options=list(region_options.keys()),
            disabled=sim_running,
            key="sim_region"
        )
        region_code = region_options[selected_region_lbl]

        current_inv = st.slider(
            "현재 재고 수준 (Units)",
            min_value=10,
            max_value=2000,
            value=120 if selected_sku == "마스크" else 300,
            step=10,
            disabled=sim_running,
            key="sim_inv"
        )

        moq = st.number_input(
            "최소 발주량 (MOQ)",
            min_value=10,
            max_value=5000,
            value=200 if selected_sku == "마스크" else 100,
            step=10,
            disabled=sim_running,
            key="sim_moq"
        )

        lot_size = st.number_input(
            "포장 단위 (Lot Size)",
            min_value=1,
            max_value=1000,
            value=50 if selected_sku == "마스크" else 10,
            step=5,
            disabled=sim_running,
            key="sim_lot"
        )

        budget_limit = st.number_input(
            "지점 예산 제한 (원)",
            min_value=500000,
            max_value=20000000,
            value=5000000 if selected_sku == "마스크" else 10000000,
            step=500000,
            disabled=sim_running,
            key="sim_budget"
        )

        drift_score = st.slider(
            "유통 시장 데이터 드리프트 스코어 (α)",
            min_value=0.0,
            max_value=3.0,
            value=0.8,
            step=0.1,
            disabled=sim_running,
            key="sim_drift"
        )

        st.markdown('</div>', unsafe_allow_html=True)

        # Simulation trigger button
        if not sim_running:
            if st.button("🚀 자율 발주 시뮬레이션 가동", type="primary", use_container_width=True):
                st.session_state["sim_running"] = True
                st.session_state["sim_completed"] = False
                st.rerun()
        else:
            st.button("⚙️ 시뮬레이터 연산 중...", disabled=True, use_container_width=True)

    with col_display:
        st.markdown('<div class="sec">🖥️ 실시간 AI 에이전트 CoT 파이프라인</div>', unsafe_allow_html=True)

        if sim_running:
            # Step by step simulation using st.status
            with st.status("🤖 SCM AI 자율 제어 에이전트 연쇄 추론 가동 중...", state="running") as status:
                status.write("📡 **DataAgent**: 실시간 재고 및 유통 시장 데이터 탐색 중...")
                time.sleep(1.5)
                
                status.write("🌡️ **IoTAgent**: RFID 카운트 및 창고 보관 텔레메트리 무결성 수집 중...")
                time.sleep(1.0)
                
                status.write("🧠 **MLAgent**: TFT 90일 분위수 확률 예측 (q10, q50, q90) 연산 가동...")
                time.sleep(2.0)
                
                status.write("⚖️ **DecisionAgent**: Gemini 2.5 리스크 감사 가드라인 및 Q_final 최종 발주량 연산...")
                time.sleep(1.5)
                
                status.write("🚀 **ActionAgent**: SCM 백엔드 자율 발주 승인 대기 또는 자동 승인 커밋 이행...")
                time.sleep(1.0)
                
                status.update(label="✅ 자율 발주 시뮬레이션 완료", state="complete")
            
            # Formulate results
            unit_price = 15000 if selected_sku == "마스크" else (550000 if selected_sku == "반도체 칩" else 80000)
            holding_cost = 5.0 if selected_sku == "마스크" else 150.0
            
            # Predict values
            d10 = int(current_inv * 0.9 + 50)
            d50 = int(current_inv * 1.1 + 100)
            d90 = int(current_inv * 1.4 + 200)
            
            safety_stock = int(d90 * 0.2)
            target_inventory = d90 + safety_stock
            net_q = target_inventory - current_inv
            
            if net_q <= 0:
                q_final = 0
            else:
                q_discrete = int((net_q + lot_size - 1) // lot_size) * lot_size
                q_final = max(moq, q_discrete)
                
            total_price = q_final * unit_price
            
            # Determine status based on constraints
            is_pending = False
            pending_reason = ""
            
            if total_price >= budget_limit:
                is_pending = True
                pending_reason = f"발주 총액({total_price:,.0f}원)이 예산 제한({budget_limit:,.0f}원)을 초과함."
            elif drift_score >= 1.5:
                is_pending = True
                pending_reason = f"데이터 드리프트 지수({drift_score:.1f})가 임계값(1.5)을 초과해 시장 이상 변동 감지됨."
            elif (d90 - d10) / d50 > 0.8:
                is_pending = True
                pending_reason = f"수요 불확실성 편차폭({(d90 - d10) / d50 * 100:.1f}%)이 관리 가이드라인(80%)을 초과함."
                
            decision_status = "PENDING" if is_pending else "AUTO_APPROVED"
            decision_reasoning = pending_reason if is_pending else "안전 재고 ROP 기준 미달 보충을 위한 최적 발주량 산출 완료."

            st.session_state["sim_results"] = {
                "sku": selected_sku,
                "region_code": region_code,
                "region_lbl": selected_region_lbl,
                "current_inv": current_inv,
                "moq": moq,
                "lot_size": lot_size,
                "budget_limit": budget_limit,
                "drift_score": drift_score,
                "unit_price": unit_price,
                "d10": d10,
                "d50": d50,
                "d90": d90,
                "safety_stock": safety_stock,
                "q_final": q_final,
                "total_price": total_price,
                "status": decision_status,
                "reasoning": decision_reasoning,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            st.session_state["sim_running"] = False
            st.session_state["sim_completed"] = True
            st.rerun()

        elif sim_completed:
            res = st.session_state["sim_results"]

            # Workflow Pipeline Diagram (HTML/CSS Step flow)
            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(255,255,255,0.02); padding: 16px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.06); margin-bottom: 16px;">
                <div style="text-align: center; flex: 1;">
                    <div style="font-size: 20px; margin-bottom: 4px;">📡</div>
                    <div style="font-size: 9px; font-weight: bold; color: #64ffda;">DataAgent</div>
                    <div style="font-size: 8px; color: #8892b0;">전처리 완료</div>
                </div>
                <div style="color: rgba(255,255,255,0.15); font-weight: bold;">➔</div>
                <div style="text-align: center; flex: 1;">
                    <div style="font-size: 20px; margin-bottom: 4px;">🌡️</div>
                    <div style="font-size: 9px; font-weight: bold; color: #64ffda;">IoTAgent</div>
                    <div style="font-size: 8px; color: #8892b0;">센서 ACTIVE</div>
                </div>
                <div style="color: rgba(255,255,255,0.15); font-weight: bold;">➔</div>
                <div style="text-align: center; flex: 1;">
                    <div style="font-size: 20px; margin-bottom: 4px;">🧠</div>
                    <div style="font-size: 9px; font-weight: bold; color: #64ffda;">MLAgent</div>
                    <div style="font-size: 8px; color: #8892b0;">TFT 추론 완료</div>
                </div>
                <div style="color: rgba(255,255,255,0.15); font-weight: bold;">➔</div>
                <div style="text-align: center; flex: 1;">
                    <div style="font-size: 20px; margin-bottom: 4px;">⚖️</div>
                    <div style="font-size: 9px; font-weight: bold; color: #64ffda;">Decision</div>
                    <div style="font-size: 8px; color: #8892b0;">리스크 감사</div>
                </div>
                <div style="color: rgba(255,255,255,0.15); font-weight: bold;">➔</div>
                <div style="text-align: center; flex: 1;">
                    <div style="font-size: 20px; margin-bottom: 4px;">🚀</div>
                    <div style="font-size: 9px; font-weight: bold; color: #64ffda;">Action</div>
                    <div style="font-size: 8px; color: #8892b0;">명령 발행</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            status_color = "g" if res["status"] == "AUTO_APPROVED" else "y"
            status_label = "자동 승인 (AUTO_APPROVED)" if res["status"] == "AUTO_APPROVED" else "수동 검토 격리 (PENDING)"

            st.markdown(f"""
            <div class="cc" style="border-left: 4px solid { '#00e5a0' if res['status'] == 'AUTO_APPROVED' else '#ffc107' };">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 15px; font-weight: 700; color: #ccd6f6;">📋 최종 의사결정 판정 결과</span>
                    <span class="kb {'ok' if res['status'] == 'AUTO_APPROVED' else 'w'}" style="font-size: 11px; margin-top:0px;">{status_label}</span>
                </div>
                <div style="font-size: 12.5px; margin-top: 10px; color: #8892b0; line-height: 1.6;">
                    • <strong>조회 일시</strong>: {res['timestamp']}<br/>
                    • <strong>대상 품목 / 지점</strong>: {res['sku']} / {res['region_lbl']}<br/>
                    • <strong>최적 추천 발주량 (Q_final)</strong>: <span style="color: #64ffda; font-weight: bold;">{res['q_final']:,} 개</span><br/>
                    • <strong>발주 총 소요액</strong>: <span style="color: #ccd6f6; font-weight: bold;">{res['total_price']:,} 원</span><br/>
                    • <strong>의사결정 판단 근거</strong>: <span style="color: #ccd6f6;">{res['reasoning']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Detail Agent Steps CoT (Detailed Markdown cards)
            st.markdown("#### 🔬 각 에이전트 상세 Chain-of-Thought")
            
            # Step 1: DataAgent
            st.markdown(f"""
            <div class="cc">
                <div class="ct">📡 DataAgent Scan Report</div>
                <div style="font-size: 11.5px; color: #8892b0;">
                    • SCM DB 스캔 완료. <strong>현재 재고: {res['current_inv']} EA</strong>.<br/>
                    • 3σ Outlier clipping 적용: 노이즈 감지되지 않음.<br/>
                    • Google Trends 충격 지수 파싱 완료. 데이터 드리프트 계수: {res['drift_score']:.1f}.
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Step 2: IoTAgent
            st.markdown(f"""
            <div class="cc">
                <div class="ct">🌡️ IoTAgent Sensor Verification</div>
                <div style="font-size: 11.5px; color: #8892b0;">
                    • 지점 {res['region_code']} 창고 RFID 리더기 통신 검증: <strong>상태 ACTIVE (100% 정상 수신)</strong>.<br/>
                    • 실시간 센서 온도: 18.5°C, 습도: 42% (가이드라인 적합).
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Step 3: MLAgent
            st.markdown(f"""
            <div class="cc">
                <div class="ct">🧠 MLAgent Temporal Fusion Transformer (TFT) Forecast</div>
                <div style="font-size: 11.5px; color: #8892b0;">
                    • 90일 시계열 데이터 분위수 예측 연산 결과:<br/>
                    &nbsp;&nbsp; - 분위수 q=0.1 (보수적 하한 수요): <strong>{res['d10']} 개</strong><br/>
                    &nbsp;&nbsp; - 분위수 q=0.5 (중간 수요 예측): <strong>{res['d50']} 개</strong><br/>
                    &nbsp;&nbsp; - 분위수 q=0.9 (비상 상한 수요): <strong>{res['d90']} 개</strong><br/>
                    • 권장 안전재고(SS): {res['safety_stock']} 개 (Service Level: 95% 기준)
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Step 4: DecisionAgent
            st.markdown(f"""
            <div class="cc">
                <div class="ct">⚖️ DecisionAgent Risk Audit</div>
                <div style="font-size: 11.5px; color: #8892b0;">
                    • 수리 모델 연산: <code>Q_final = Max(MOQ, Ceil((D90 + SS - CurrentStock) / LotSize) * LotSize)</code><br/>
                    &nbsp;&nbsp; -> Calculated Net Q: {res['d90'] + res['safety_stock'] - res['current_inv']} EA.<br/>
                    &nbsp;&nbsp; -> MOQ & Lot Size 보정 적용 완료: <strong>Q_final = {res['q_final']} 개</strong>.<br/>
                    • 리스크 감사 결과: 상태코드 <strong>{res['status']}</strong>.
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Step 5: ActionAgent
            st.markdown(f"""
            <div class="cc">
                <div class="ct">🚀 ActionAgent Execution</div>
                <div style="font-size: 11.5px; color: #8892b0;">
                    • 발주 제안 프로포설 생성 및 REST API 발행 예약 완료.<br/>
                    • 감사 로그(Audit Logs) 및 실시간 토스트 알림 대기열 등록 완료.
                </div>
            </div>
            """, unsafe_allow_html=True)

            # HITL Action Interface
            if res["status"] == "AUTO_APPROVED":
                st.success("🟢 자율 승인 조건이 모두 충족되었습니다. 추가 수동 승인 없이 최종 자율 발주가 확정되었습니다.")
                if st.button("📥 새로운 시뮬레이션 가동 준비"):
                    st.session_state["sim_completed"] = False
                    st.rerun()
            else:
                st.warning("⚠️ 리스크 통제 가이드라인 초과로 인해 본 발주 제안은 **수동 승인 대기(PENDING)** 상태로 격리되었습니다.")
                
                hitl_col1, hitl_col2 = st.columns([1, 1])
                with hitl_col1:
                    if st.button("📥 PENDING 예외 강제 승인", type="primary", use_container_width=True):
                        st.toast(f"🟢 [HITL] {res['sku']} 발주 강제 승인 처리 성공!")
                        st.success("발주가 예외 승인되어 backend 전송 큐에 등록되었습니다.")
                with hitl_col2:
                    if st.button("❌ 발주 최종 반려", use_container_width=True):
                        st.toast(f"🔴 [HITL] {res['sku']} 발주 반려 완료.")
                        st.warning("발주 제안이 최종 기각되었습니다.")

        else:
            st.info("💡 좌측 패널에서 시뮬레이터 파라미터를 설정한 후 [자율 발주 시뮬레이션 가동] 버튼을 누르시면 각 SCM 에이전트의 CoT(생각 체인) 파이프라인이 시연됩니다.")

if __name__ == "__main__":
    render_agent_workflow()
