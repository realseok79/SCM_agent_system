# dashboard/views/agent_workflow.py
import streamlit as st
import time
import pandas as pd
from datetime import datetime
import auth_helper
from components.styles import inject_custom_css

def render_agent_workflow():
    # Load custom styles (background has been updated to native dark mode)
    inject_custom_css()

    st.title("SCM AI 자율 제어 에이전트 워크플로우")
    st.caption("AI 기반 다중 에이전트(Multi-Agent) 및 데이터 최적화 기반 공급망 관리 제어 시스템 시뮬레이터")
    st.markdown("---")

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

    col_ctrl, col_display = st.columns([1, 2.5])

    with col_ctrl:
        st.subheader("시뮬레이션 설정 파라미터")
        selected_sku = st.selectbox("분석 SKU 선택", options=["반도체 칩", "마스크", "종합 품목"], disabled=sim_running)
        selected_region_lbl = st.selectbox("대상 지점 선택", options=list(region_options.keys()), disabled=sim_running)
        region_code = region_options[selected_region_lbl]

        current_inv = st.slider("현재 재고 수준 (Units)", 10, 2000, 120 if selected_sku == "마스크" else 300, 10, disabled=sim_running)
        moq = st.number_input("최소 발주량 (MOQ)", 10, 5000, 200 if selected_sku == "마스크" else 100, 10, disabled=sim_running)
        lot_size = st.number_input("포장 단위 (Lot Size)", 1, 1000, 50 if selected_sku == "마스크" else 10, 5, disabled=sim_running)
        budget_limit = st.number_input("지점 예산 제한 (원)", 500000, 1000000000, 5000000 if selected_sku == "마스크" else 10000000, 500000, disabled=sim_running)
        drift_score = st.slider("데이터 드리프트 지수 (α)", 0.0, 3.0, 0.8, 0.1, disabled=sim_running)

        if not sim_running:
            if st.button("자율 발주 시뮬레이션 가동", type="primary"):
                st.session_state["sim_running"] = True
                st.session_state["sim_completed"] = False
                st.rerun()
        else:
            st.button("시뮬레이터 연산 중...", disabled=True)

    with col_display:
        if sim_running:
            with st.status("SCM AI 자율 제어 에이전트 연쇄 추론 가동 중...", state="running") as status:
                status.write("DataAgent: 실시간 재고 및 유통 시장 데이터 탐색 중...")
                time.sleep(1.0)
                status.write("IoTAgent: RFID 카운트 및 창고 보관 텔레메트리 무결성 수집 중...")
                time.sleep(1.0)
                status.write("MLAgent: TFT 90일 분위수 확률 예측 (q10, q50, q90) 연산 가동...")
                time.sleep(1.0)
                status.write("DecisionAgent: 리스크 감사 가드라인 및 최종 발주량 연산...")
                time.sleep(1.0)
                status.write("ActionAgent: SCM 백엔드 자율 발주 승인 대기 또는 커밋 이행...")
                time.sleep(1.0)
                status.update(label="자율 발주 시뮬레이션 완료", state="complete")
            
            unit_price = 15000 if selected_sku == "마스크" else (550000 if selected_sku == "반도체 칩" else 80000)
            
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
            
            # Constraints Check
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
            decision_reasoning = pending_reason if is_pending else "안전 범주 내의 정상 발주 건"

            st.session_state["sim_results"] = {
                "sku": selected_sku,
                "region_lbl": selected_region_lbl,
                "current_inv": current_inv,
                "moq": moq, "lot_size": lot_size,
                "drift_score": drift_score,
                "d10": d10, "d50": d50, "d90": d90,
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
            res = st.session_state.get("sim_results", {})
            sku = res.get("sku", "반도체 칩")
            region_lbl = res.get("region_lbl", "기본 관제소")
            current_inv = res.get("current_inv", 300)
            moq = res.get("moq", 100)
            lot_size = res.get("lot_size", 10)
            drift_score = res.get("drift_score", 0.8)
            d10 = res.get("d10", 320)
            d50 = res.get("d50", 430)
            d90 = res.get("d90", 620)
            safety_stock = res.get("safety_stock", 124)
            q_final = res.get("q_final", 450)
            total_price = res.get("total_price", 247500000)
            status = res.get("status", "PENDING")
            reasoning = res.get("reasoning", "")
            timestamp = res.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

            # 1. DataAgent & IoTAgent: 실시간 공급망 리스크 인덱스 및 텔레메트리
            st.markdown("### 1. DataAgent & IoTAgent: 실시간 공급망 리스크 인덱스 및 텔레메트리")
            st.markdown("<p style='font-size: 13.5px; color: #8892b0;'>내부 적재 데이터와 외부 오픈 API 스트림을 실시간 융합하여 종합 물류 리스크를 선제 산출합니다.</p>", unsafe_allow_html=True)
            
            # Calculate dynamic risk score based on drift_score
            risk_score = int(45 + drift_score * 20)
            risk_score = min(risk_score, 100)
            risk_lbl = "⚠️ 주의 (이상 변동 감지)" if risk_score >= 60 else "🟢 정상 (안정적 관리)"
            
            # Map region to real SCM port names dynamically
            port_map = {
                "서울": "인천항 (Incheon Port)",
                "수도권": "인천항 (Incheon Port)",
                "인천": "인천항 (Incheon Port)",
                "경기": "인천항 (Incheon Port)",
                "부산": "부산항 (Busan Port)",
                "영남": "부산항 (Busan Port)",
                "경남": "부산항 (Busan Port)",
                "제주": "제주항 (Jeju Port)",
                "광주": "광양항 (Gwangyang Port)",
                "전남": "광양항 (Gwangyang Port)",
            }
            
            port_name = "부산항 (Busan Port)"  # default fallback
            for keyword, name in port_map.items():
                if keyword in region_lbl:
                    port_name = name
                    break
                    
            # Compute dynamic wait time and delta based on drift score and region hash
            wait_days = round(1.0 + drift_score * 1.6 + (hash(region_lbl) % 3) * 0.3, 1)
            delta_days = round(drift_score * 0.5, 1)
            
            if drift_score >= 1.2:
                port_val = f"대기 {wait_days}일"
                port_delta = f"↑ {port_name} 적체 가중 (+{delta_days}일)"
                port_delta_color = "inverse"
            else:
                port_val = f"대기 {wait_days}일"
                port_delta = f"🟢 {port_name} 원활 (정상 소요)"
                port_delta_color = "normal"
            
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric(
                    label="종합 공급망 리스크 지수", 
                    value=f"{risk_score} / 100", 
                    delta=risk_lbl, 
                    delta_color="inverse" if risk_score >= 60 else "normal"
                )
            with m2:
                st.metric(
                    label="데이터 드리프트 지수 (α)", 
                    value=f"{drift_score:.2f}", 
                    delta="↑ 임계값 초과 위험" if drift_score >= 1.5 else "안정 범주",
                    delta_color="inverse" if drift_score >= 1.5 else "normal"
                )
            with m3:
                st.metric(
                    label="항만 혼잡도 (Spire Maritime)", 
                    value=port_val, 
                    delta=port_delta,
                    delta_color=port_delta_color
                )
            with m4:
                st.metric(
                    label="거시경제 지표 (FRED / WTI)", 
                    value="$78.42 / bbl", 
                    delta="↑ 전일 대비 -1.25%",
                    delta_color="normal"
                )

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("---")

            # 2. DecisionAgent: 환각 통제형 대수적 수리 필터 가드레일 (XAI)
            st.markdown("### 2. DecisionAgent: 환각 통제형 대수적 수리 필터 가드레일 (XAI)")
            st.markdown("<p style='font-size: 13.5px; color: #8892b0;'>AI 에이전트의 무작위 발주량 생성 리스크(Hallucination)를 원천 차단하기 위해, 1차적으로 제약 조건 수리 필터를 강제 통과시킵니다.</p>", unsafe_allow_html=True)
            
            # Draw real dynamic table based on simulation result
            filter_data = pd.DataFrame([{
                "대상 지점": region_lbl,
                "분석 SKU": sku,
                "TFT 딥러닝 예측 (D90)": f"{d90:,} 개",
                "안전재고 (SS)": f"{safety_stock:,} 개",
                "MOQ (최소발주량)": f"{moq:,} 개",
                "Lot Size (포장단위)": f"{lot_size:,} 개",
                "최종 추천 발주량 (Q_final)": f"{q_final:,} 개",
                "시스템 무결성 검증": "수리 가드레일 통과"
            }])
            
            st.dataframe(filter_data, use_container_width=True, hide_index=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("---")

            # 3. ActionAgent: 결함 허용(Fault-Tolerance) 하이브리드 결재 워크플로우 큐
            st.markdown("### 3. ActionAgent: 결함 허용(Fault-Tolerance) 하이브리드 결재 워크플로우 큐")
            st.markdown("<p style='font-size: 13.5px; color: #8892b0;'>DecisionAgent가 1차 검증한 발주 수치를 기반으로, 실시간 리스크를 평가하여 결재 라인을 하이브리드 분기(AUTO_APPROVED / PENDING)합니다.</p>", unsafe_allow_html=True)

            tab1, tab2 = st.tabs(["자동 승인 내역 (AUTO_APPROVED)", "수동 결재 대기 큐 (PENDING)"])

            with tab1:
                if status == "AUTO_APPROVED":
                    st.success("안전 범주 내의 일상적 발주 건으로, 담당자 개입 없이 시스템이 자율적으로 SCM 백엔드에 최종 적재를 완료했습니다.")
                    df_auto = pd.DataFrame([{
                        "발주 ID": f"ORD-{timestamp.replace('-', '').replace(':', '').replace(' ', '-')[:15]}-01",
                        "대상 창고": region_lbl,
                        "분석 SKU": sku,
                        "최종 발주량": f"{q_final:,} 개",
                        "리스크 등급": "정상 (Low)",
                        "상태": "AUTO_APPROVED"
                    }])
                    st.dataframe(df_auto, use_container_width=True, hide_index=True)
                else:
                    st.info("💡 현재 자율 자동 승인된 발주 내역이 없습니다. (수동 결재 대기 큐를 확인해 주세요)")
                
                if st.button("새로운 시뮬레이션 가동 시작", type="primary"):
                    st.session_state["sim_completed"] = False
                    st.rerun()

            with tab2:
                if status == "PENDING":
                    st.warning("외부 돌발 공급망 충격 예외 상황 감지 또는 예산 임계치 초과로 인해 격리된 수동 승인 대기 큐입니다.")
                    st.markdown(f"**격리 감지 사유**: `{reasoning}`")
                    df_pending = pd.DataFrame([{
                        "발주 ID": f"ORD-{timestamp.replace('-', '').replace(':', '').replace(' ', '-')[:15]}-02",
                        "대상 창고": region_lbl,
                        "분석 SKU": sku,
                        "최종 발주량": f"{q_final:,} 개",
                        "리스크 등급": "주의 (High)" if drift_score >= 1.5 or "예산" in reasoning else "경고 (Medium)",
                        "상태": "PENDING"
                    }])
                    st.dataframe(df_pending, use_container_width=True, hide_index=True)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    c_btn1, c_btn2, c_btn3 = st.columns(3)
                    with c_btn1:
                        if st.button("현업 피드백 피딩 후 반려", key="btn_hitl_rej"):
                            st.toast("🚫 발주 반려 완료.")
                            st.warning("발주 제안이 기각되었습니다.")
                    with c_btn2:
                        if st.button("수량 수정 후 재연산 요청", key="btn_hitl_recalc"):
                            st.toast("🔄 수량 수정 및 재연산 성공!")
                    with c_btn3:
                        if st.button("강제 발주 승인 (Human-in-the-Loop)", key="btn_hitl_app"):
                            st.toast("🟢 예외 승인 처리 성공!")
                            st.success("SCM 백엔드 적재 완료!")
                else:
                    st.success("🟢 현재 수동 결재 검토가 필요한 격리 건이 존재하지 않습니다.")
        else:
            st.info("좌측 패널에서 파라미터를 조절한 뒤 [자율 발주 시뮬레이션 가동] 버튼을 누르시면, 우측에 렌더링된 결과를 보실 수 있습니다.")

if __name__ == "__main__":
    render_agent_workflow()
