# dashboard/views/mlops_simulator.py
import streamlit as st
import pandas as pd
import numpy as np
import requests
import os
import plotly.graph_objects as go
import plotly.express as px

# FastAPI ML API 엔드포인트 URL 설정
ML_API_URL = os.environ.get("ML_API_URL", "http://localhost:8000")

def render_mlops_simulator_dashboard():
    # ── 커스텀 메인 헤더 디자인 ──
    st.markdown("""
    <div class="hdr" style="margin-bottom: 20px;">
        <div>
            <div class="hdr-t" style="font-size: 26px; color: #8ab4f8; font-weight: 700;">🤖 SCM 하이브리드 MLOps 운영 시뮬레이터</div>
            <div class="hdr-s" style="font-size: 13px; color: #9aa0a6;">
                TFT 분위수 예측 모델 서빙 최적화, SHAP 설명성, Human-in-the-Loop 의사결정 제어 및 데이터 드리프트 CT 트리거 통합 관제탑
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── MLOps 시뮬레이터 제어판 (좌측 입력, 우측 실시간 시뮬레이션 지표) ──
    st.markdown('<div class="sec" style="font-size: 16px; font-weight: 600; color: #e8eaed; border-bottom: 2px solid #3c4043; padding-bottom: 6px;">⚙️ 하이브리드 MLOps 실시간 인프라 시뮬레이션</div>', unsafe_allow_html=True)
    
    col_ctrl, col_stats = st.columns([1, 1.2])

    with col_ctrl:
        st.markdown('<div style="background: #292a2d; padding: 15px; border-radius: 8px; border: 1px solid #3c4043;">', unsafe_allow_html=True)
        st.subheader("🎛️ 인프라 및 가드라인 제어")
        
        # 슬라이더 1: 오차 임계치 가드라인
        threshold = st.slider(
            "⚠️ 오차 임계치 가드라인 (MAE Limit, %)", 
            min_value=5, max_value=30, value=15, step=1,
            help="이 임계치를 실제 예측 오차가 초과하면 데이터 드리프트가 판정되고 자동 재학습(CT)이 활성화됩니다."
        )
        
        # 슬라이더 2: Gunicorn 할당 워커 프로세스 수
        workers = st.slider(
            "💻 Gunicorn 할당 워커 프로세스 수", 
            min_value=1, max_value=8, value=4, step=1,
            help="FastAPI 병렬 추론 처리를 위한 Gunicorn 비동기 Uvicorn 워커 수입니다."
        )
        
        # 슬라이더 3: 일일 배치 발주 품목 규모
        batch_scale = st.slider(
            "📦 일일 배치 발주 품목 규모 (Items)", 
            min_value=1000, max_value=20000, value=5000, step=500,
            help="하루에 처리하는 총 발주 예측 대상 스쿠(SKU) 규모입니다."
        )
        
        # 드롭다운: 현재 유통 시장 데이터 상태
        market_state = st.selectbox(
            "📊 유통 시장 실시간 데이터 상태 (Drift 여부)",
            options=["정상 수요 패턴 (Normal)", "급격한 시장 변동 (Drift 발생)"],
            help="급격한 코로나 유행, 성수기, 혹은 공급망 충격 발생 시 실제 오차가 급증하여 드리프트가 발생합니다."
        )
        
        # ONNX 최적화 여부 토글 (GIL 우회 핵심 변수)
        onnx_comp = st.checkbox("⚡ ONNX 추론 가속 컴파일 활성화 (GIL 비동기 최적화)", value=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

    # ── MLOps 시뮬레이터 수리 연산 및 출력 ──
    # 1. 지연 시간 (Latency, ms) 수리 공식 계산
    # ONNX 적용 시 연산 속도 70% 감소 보정
    onnx_factor = 0.3 if onnx_comp else 1.0
    base_latency_per_item = 0.05 * onnx_factor # ONNX 시 개당 0.015ms, 일반 시 0.05ms
    
    # 지연 시간(ms) = (배치 규모 / (워커 수 * 80)) * 개당 지연시간에 비례하도록 설계
    sim_latency = (batch_scale / (workers * 80)) * base_latency_per_item * 1000
    sim_latency = max(2.5, round(sim_latency, 1)) # 최소 2.5ms 보장

    # 2. 시스템 스루풋 (Throughput, items/sec)
    sim_throughput = int((workers * 1500) / onnx_factor)
    
    # 3. 데이터 드리프트 및 CT 상태 판정
    if market_state == "정상 수요 패턴 (Normal)":
        sim_drift_error = 9.2 + np.random.uniform(-0.5, 0.5)
    else:
        sim_drift_error = 22.4 + np.random.uniform(-1.0, 1.0)
        
    sim_drift_error = round(sim_drift_error, 2)
    drift_triggered = sim_drift_error > threshold

    with col_stats:
        # 실시간 성능 메트릭 렌더링
        st.markdown('<div class="kg">', unsafe_allow_html=True)
        
        # 메트릭 1: 지연 시간
        lat_color = "g" if sim_latency < 100 else ("y" if sim_latency < 300 else "r")
        st.markdown(f"""
        <div class="kc">
            <div class="kl">평균 추론 지연 시간</div>
            <div class="kv {lat_color}">{sim_latency} ms</div>
            <div class="ku">목표치: < 150ms 이내</div>
        </div>
        """, unsafe_allow_html=True)
        
        # 메트릭 2: 처리 성능
        st.markdown(f"""
        <div class="kc">
            <div class="kl">최대 추론 처리량</div>
            <div class="kv b">{sim_throughput:,} SKU/s</div>
            <div class="ku">ONNX 최적화 배율 적용</div>
        </div>
        """, unsafe_allow_html=True)
        
        # 메트릭 3: 데이터 드리프트 오차
        drift_color = "r" if drift_triggered else "g"
        st.markdown(f"""
        <div class="kc">
            <div class="kl">실시간 SCM MAE 오차</div>
            <div class="kv {drift_color}">{sim_drift_error} %</div>
            <div class="ku">가드라인 임계치: {threshold}%</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # 상태 판정 상세 리포트
        st.markdown("#### 🔍 MLOps 운영 모니터링 분석")
        if drift_triggered:
            st.error(f"🚨 **[데이터 드리프트 경보 활성화]** 현재 SCM 예측 오차({sim_drift_error}%)가 설정한 임계치 가드라인({threshold}%)을 초과하여 급격한 시장 변동이 감지되었습니다! AI 엔진의 재학습(CT)이 요구됩니다.")
            
            # 지속적 학습 (CT) 즉시 트리거 버튼
            if st.button("🔄 CT 자동 재학습 즉시 트리거 (POST /api/v1/ml/train)", type="primary"):
                with st.spinner("🚀 FastAPI CT 전이학습 파이프라인 가동 중... (인코더 동결, 디코더 역전파 미세조정)"):
                    try:
                        # FastAPI 서버에 CT 요청 전송
                        payload = {
                            "company_id": "SIGMA",
                            "item_id": "MASK_01",
                            "historical_sales": [
                                {"date": f"2026-05-{i:02d}", "qty": float(100 + i * 5 + np.random.randint(-15, 15))} 
                                for i in range(1, 25)
                            ],
                            "hyperparameters": {
                                "epochs": 5,
                                "learning_rate": 0.002
                            }
                        }
                        res = requests.post(f"{ML_API_URL}/api/v1/ml/train", json=payload, timeout=20)
                        if res.status_code == 200:
                            data = res.json()
                            st.success(f"🎉 **CT 미세조정 완료!** 신규 버전: `{data['trained_model_version']}` | 최종 MAE: `{data['metrics']['mae']}`")
                            st.toast("🔔 [CT Pipeline] TFT 글로벌 모델 미세조정 학습 가중치 업데이트 성공!")
                        else:
                            st.error(f"❌ CT 트리거 실패: {res.text}")
                    except Exception as e:
                        st.error(f"❌ API 서버 연결 실패: {e}. FastAPI `ml-api` 컨테이너 상태를 점검하십시오.")
        else:
            st.success("✅ **[안정 상태]** 예측 오차가 가드라인 이내로 통제되고 있습니다. 추가적인 인프라 보정이나 재학습이 필요하지 않습니다.")
            
        # 가중치 및 시스템 리소스 모니터링 가상 게이지
        cpu_load = min(100, int((sim_throughput / 15000) * 100))
        st.markdown(f"**🖥️ ML-API 컨테이너 CPU 부하 시뮬레이션** ({cpu_load}%)")
        st.progress(cpu_load / 100.0)

    st.write("")

    # ── Phase 6: 설명 가능한 AI (XAI) 및 실시간 TFT 하이브리드 수요 예측 ──
    st.markdown('<div class="sec" style="font-size: 16px; font-weight: 600; color: #e8eaed; border-bottom: 2px solid #3c4043; padding-bottom: 6px;">🧠 실시간 TFT 하이브리드 수요 예측 및 SHAP 기여도 산출</div>', unsafe_allow_html=True)
    
    col_inputs, col_xai = st.columns([1, 1.2])
    
    with col_inputs:
        st.subheader("📊 신규 발주 예측 대상 데이터 입력")
        item_id = st.text_input("품목 ID (SKU)", "MASK_A01")
        region_code = st.text_input("지점 코드 (Region)", "KR-11")
        
        # 30일치 가짜 과거 판매량 슬라이더 입력기
        base_sales = st.slider("평균 일일 판매량 설정 (최근 30일 기준)", min_value=50, max_value=1000, value=250, step=10)
        
        # 공휴일 영향 토글
        is_holiday = st.checkbox("🎉 예측 대상 기간 중 초대형 유통 행사 / 명절 연휴 포함 여부", value=True)
        
        # API 예측 호출용 가짜 과거 판매량 구성
        sales_records = []
        for i in range(30):
            sales_records.append({
                "date": f"2026-04-{i+1:02d}",
                "qty": float(base_sales + np.random.randint(-30, 30))
            })
            
        future_events = [{"date": "2026-05-01", "is_holiday": is_holiday, "event_type": "PROMOTION" if is_holiday else "NORMAL"}]
        
        if st.button("🔮 TFT 하이브리드 고속 추론 및 SHAP 산출 실행", type="secondary"):
            with st.spinner("🧠 API 서버에서 분위수(Pinball Loss) 고속 연산 및 SHAP 기여도 분석 중..."):
                try:
                    payload = {
                        "item_id": item_id,
                        "region_code": region_code,
                        "recent_sales": sales_records,
                        "future_events": future_events
                    }
                    
                    res = requests.post(f"{ML_API_URL}/api/v1/ml/predict-demand-hybrid", json=payload, timeout=10)
                    if res.status_code == 200:
                        pred_data = res.json()
                        st.session_state["tft_pred_result"] = pred_data
                        st.toast("⚡ [Inference Run] TFT ONNX/PyTorch 하이브리드 실시간 추론 연산 성공!")
                    else:
                        st.error(f"❌ API 추론 실패: {res.text}")
                except Exception as e:
                    st.error(f"❌ API 서버 연결 실패: {e}. FastAPI `ml-api` 컨테이너 상태를 확인하세요.")
                    
        # 이전 결과 표시
        pred_result = st.session_state.get("tft_pred_result", None)
        if pred_result:
            st.markdown(f"""
            <div style="background: #202124; padding: 12px; border-radius: 6px; border-left: 4px solid #8ab4f8; margin-top: 10px;">
                <strong>⚡ AI 예측 결과분포 (분위수 예측)</strong><br/>
                • 모델 버전: <code>{pred_result['model_version']}</code><br/>
                • 분위수 q=0.1 (하한 예측): <span style='color:#f28b82; font-weight:bold;'>{pred_result['predicted_demand_10']} 개</span><br/>
                • 분위수 q=0.5 (중간 예측): <span style='color:#8ab4f8; font-weight:bold;'>{pred_result['predicted_demand_50']} 개</span><br/>
                • 분위수 q=0.9 (상한 예측): <span style='color:#81c995; font-weight:bold;'>{pred_result['predicted_demand_90']} 개</span>
            </div>
            """, unsafe_allow_html=True)

    with col_xai:
        st.subheader("👁️ XAI (SHAP Waterfall) 요인별 가치 기여도")
        if pred_result:
            # SHAP 폭포수 차트 렌더링
            shap = pred_result["shap_values"]
            features = list(shap.keys())
            values = list(shap.values())
            
            # Plotly 수평 바 차트를 활용해 SHAP Waterfall 렌더링
            # 긍정 기여(#81c995)와 부정 기여(#f28b82) 컬러 매핑
            colors = ["#81c995" if v >= 0 else "#f28b82" for v in values]
            
            fig_shap = go.Figure()
            fig_shap.add_trace(go.Bar(
                y=[f"피처: {f}" for f in features],
                x=values,
                orientation='h',
                marker_color=colors,
                text=[f"+{v}" if v >= 0 else f"{v}" for v in values],
                textposition='auto',
                name='SHAP Value'
            ))
            
            fig_shap.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e8eaed'),
                xaxis=dict(gridcolor='#3c4043', title="SHAP 기여도 값 (최종 수요에 미치는 편차 가산율)"),
                yaxis=dict(gridcolor='#3c4043'),
                margin=dict(l=40, r=40, t=10, b=40)
            )
            st.plotly_chart(fig_shap, use_container_width=True)
            
            st.markdown("""
            💡 **SHAP 해석 가이드:**
            - **lag_1**: 전날 판매량의 연속성 기여 가중치입니다.
            - **is_holiday**: 공휴일/프로모션 지정에 따른 +20% 추가 가산 편향 강도입니다.
            - **rolling_mean_7**: 최근 7일간의 이동 평균 패턴이 예측치에 기여하는 지분율입니다.
            """)
        else:
            st.info("💡 좌측의 [TFT 하이브리드 고속 추론 및 SHAP 산출 실행] 버튼을 클릭하면 설명 가능한 AI 분석 결과가 렌더링됩니다.")

    st.write("")

    # ── Human-in-the-Loop (의사결정 제어권) 제어 센터 ──
    st.markdown('<div class="sec" style="font-size: 16px; font-weight: 600; color: #e8eaed; border-bottom: 2px solid #3c4043; padding-bottom: 6px;">🟢 Human-in-the-Loop (HITL) 예외 발주 승인 및 거절 통제소</div>', unsafe_allow_html=True)
    st.write("안전 재공 차이를 초과하거나 불확실성(분위수 10% ~ 90% 편차)이 임계치를 초과하여 수동 검토(`PENDING`) 상태로 격리된 발주 목록입니다. 현업 담당자는 데이터를 검토 후 승인 혹은 거절할 수 있습니다.")
    
    # 세션 상태에 HITL 가짜 데이터 스캐폴딩
    if "hitl_pending_orders" not in st.session_state:
        st.session_state["hitl_pending_orders"] = [
            {
                "id": "ORD-20260521-01",
                "item_id": "MASK_A01",
                "region": "서울특별시 관제소 (KR-11)",
                "ai_predicted_50": 340,
                "uncertainty_gap": 210, # q90 - q10 오차
                "suggested_order_qty": 450,
                "status": "PENDING",
                "reason": "🚨 분위수 불확실성 편차 과다 발생 (q90-q10 > 200)"
            },
            {
                "id": "ORD-20260521-02",
                "item_id": "SEMI_CHIP_X1",
                "region": "부산광역시 물류센터 (KR-21)",
                "ai_predicted_50": 1820,
                "uncertainty_gap": 950,
                "suggested_order_qty": 2000,
                "status": "PENDING",
                "reason": "🚨 MOQ(최소 발주량) 초과 급상승"
            }
        ]

    pending_list = st.session_state["hitl_pending_orders"]
    
    # 테이블 대신 아름다운 반응형 카드 형태 디자인으로 렌더링
    for idx, order in enumerate(pending_list):
        if order["status"] == "PENDING":
            st.markdown(f"""
            <div style="background: #292a2d; border: 1px solid #3c4043; border-radius: 8px; padding: 15px; margin-bottom: 12px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:14px; font-weight:bold; color:#8ab4f8;">📦 발주 번호: {order['id']}</span>
                    <span style="background:#fdd66322; color:#fdd663; border: 1px solid #fdd66355; border-radius:3px; padding: 2px 8px; font-size:10px;">{order['status']}</span>
                </div>
                <div style="font-size: 12px; margin-top: 8px; color: #e8eaed;">
                    • <strong>대상 품목 / 지점</strong>: {order['item_id']} / {order['region']}<br/>
                    • <strong>AI 중간값 예측수요 (q=50%)</strong>: {order['ai_predicted_50']:,} 개<br/>
                    • <strong>수요 불확실성 편차폭 (q90 - q10)</strong>: <span style="color:#f28b82;">{order['uncertainty_gap']:,} 개</span><br/>
                    • <strong>추천 발주 공급량 (MOQ 보정 완료)</strong>: <span style="color:#81c995; font-weight:bold;">{order['suggested_order_qty']:,} 개</span><br/>
                    • <strong>시스템 수동 격리 사유</strong>: <span style="color:#fdd663; font-weight:bold;">{order['reason']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # 사용자 액션용 컬럼 분할
            col_act1, col_act2, col_act3 = st.columns([1, 1, 4])
            with col_act1:
                if st.button("🟢 최종 승인", key=f"app_{order['id']}"):
                    order["status"] = "APPROVED"
                    st.success(f"✅ {order['id']} 발주가 성공적으로 **승인**되어 Java backend 전송 큐에 등록되었습니다.")
                    st.toast(f"🟢 [HITL] {order['id']} 승인 처리 완료.")
                    st.rerun()
            with col_act2:
                if st.button("🔴 수정 및 거절", key=f"rej_{order['id']}"):
                    order["status"] = "REJECTED"
                    st.warning(f"❌ {order['id']} 발주가 **반려 및 차단**되었습니다.")
                    st.toast(f"🔴 [HITL] {order['id']} 반려 처리 완료.")
                    st.rerun()
            with col_act3:
                st.write("")
    
    # 처리 완료된 항목 요약 표시
    processed_orders = [o for o in pending_list if o["status"] != "PENDING"]
    if processed_orders:
        with st.expander("✅ 실시간 HITL 처리 완료 이력 (최근 5건)", expanded=False):
            for po in processed_orders:
                st.write(f"• 발주 `{po['id']}` -> 상태: `{po['status']}` ({po['region']})")

if __name__ == "__main__":
    render_mlops_simulator_dashboard()
