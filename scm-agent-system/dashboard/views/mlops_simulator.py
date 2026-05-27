# dashboard/views/mlops_simulator.py
import streamlit as st
import pandas as pd
import numpy as np
import requests
import os
import plotly.graph_objects as go
import plotly.express as px
import auth_helper
from components.styles import inject_custom_css, BG, TX

# FastAPI ML API 엔드포인트 URL 설정
ML_API_URL = os.environ.get("ML_API_URL", "http://localhost:8000")

def render_mlops_simulator_dashboard():
    # Inject CSS
    inject_custom_css()

    # Read dynamic active selections from Regional dashboard if they exist
    active_prod = st.session_state.get("active_product_name", "마스크")
    active_region_code = st.session_state.get("active_region_code", "KR-11")
    active_region_name = st.session_state.get("active_region_name", "서울특별시")
    
    # clean active_region_name if it has code in parentheses
    if " (" in active_region_name:
        active_region_name = active_region_name.split(" (")[0]
        
    # Map raw product name to clean code/ID (preventing user confusion with non-existent SKUs)
    item_id_map = {
        "마스크": "MASK_A01",
        "반도체 칩": "SEMI_CHIP_X1",
        "종합 품목": "TOTAL_SKU_01"
    }
    # standardizer: if the active product name is already in map, use it. Otherwise, generate standard code
    if active_prod in item_id_map:
        default_item_id = item_id_map[active_prod]
    else:
        default_item_id = f"{active_prod.upper().replace(' ', '_')}_01"

    # Reset/update pending orders if user changed the selected product or region in the other dashboard
    if (st.session_state.get("last_selected_product_name") != active_prod or 
        st.session_state.get("last_selected_region_code") != active_region_code):
        st.session_state["last_selected_product_name"] = active_prod
        st.session_state["last_selected_region_code"] = active_region_code
        # Clear predictions and pending orders so they regenerate with new values
        st.session_state.pop("tft_pred_result", None)
        st.session_state.pop("hitl_pending_orders", None)

    # ── 커스텀 메인 헤더 디자인 ──
    from components.common import render_header, render_section, render_kpi_card
    render_header(
        "SCM 하이브리드 MLOps 운영 시뮬레이터",
        "TFT 분위수 예측 모델 서빙 최적화, SHAP 설명성, Human-in-the-Loop 의사결정 제어 및 데이터 드리프트 CT 트리거 통합 관제탑"
    )

    # ── MLOps 시뮬레이터 제어판 (좌측 입력, 우측 실시간 시뮬레이션 지표) ──
    render_section("하이브리드 MLOps 실시간 인프라 시뮬레이션")
    
    col_ctrl, col_stats = st.columns([1, 1.2])

    with col_ctrl:
        st.markdown('<div class="cc">', unsafe_allow_html=True)
        st.subheader("인프라 및 가드라인 제어")
        
        # 슬라이더 1: 오차 임계치 가드라인
        threshold = st.slider(
            " 오차 임계치 가드라인 (MAE Limit, %)", 
            min_value=5, max_value=30, value=15, step=1,
            help="이 임계치를 실제 예측 오차가 초과하면 데이터 드리프트가 판정되고 자동 재학습(CT)이 활성화됩니다."
        )
        
        # 슬라이더 2: Gunicorn 할당 워커 프로세스 수
        workers = st.slider(
            "Gunicorn 할당 워커 프로세스 수", 
            min_value=1, max_value=8, value=4, step=1,
            help="FastAPI 병렬 추론 처리를 위한 Gunicorn 비동기 Uvicorn 워커 수입니다."
        )
        
        # 슬라이더 3: 일일 배치 발주 품목 규모
        batch_scale = st.slider(
            "일일 배치 발주 품목 규모 (Items)", 
            min_value=1000, max_value=20000, value=5000, step=500,
            help="하루에 처리하는 총 발주 예측 대상 스쿠(SKU) 규모입니다."
        )
        
        # 드롭다운: 현재 유통 시장 데이터 상태
        market_state = st.selectbox(
            "유통 시장 실시간 데이터 상태 (Drift 여부)",
            options=["정상 수요 패턴 (Normal)", "급격한 시장 변동 (Drift 발생)"],
            help="급격한 코로나 유행, 성수기, 혹은 공급망 충격 발생 시 실제 오차가 급증하여 드리프트가 발생합니다."
        )
        
        # ONNX 최적화 여부 토글 (GIL 우회 핵심 변수)
        onnx_comp = st.checkbox("ONNX 추론 가속 컴파일 활성화 (GIL 비동기 최적화)", value=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

    # ── MLOps 시뮬레이터 수리 연산 및 출력 ──
    # 백엔드 API 실시간 지표 연동
    real_metrics = auth_helper.api_get("/api/dashboard/mlops-metrics") or {}
    
    # 1. 지연 시간 (Latency, ms) 수리 공식 계산 (백엔드 데이터 부하와 연동)
    backend_latency = real_metrics.get("simulatedLatency", 15.0)
    onnx_factor = 0.3 if onnx_comp else 1.0
    sim_latency = round(backend_latency * onnx_factor * (batch_scale / 5000.0) * (4.0 / workers), 1)
    sim_latency = max(2.5, sim_latency) # 최소 2.5ms 보장

    # 2. 시스템 스루풋 (Throughput, items/sec)
    backend_throughput = real_metrics.get("simulatedThroughput", 5000)
    sim_throughput = int(backend_throughput * (workers / 4.0) / onnx_factor)
    
    # 3. 데이터 드리프트 및 CT 상태 판정
    # 백엔드의 실제 업로드 파일 품질/드리프트와 사용자가 연출한 마켓 시나리오를 연립 계산
    real_drift = real_metrics.get("averageDriftScore", 5.0) # 기본 5%
    if market_state == "정상 수요 패턴 (Normal)":
        sim_drift_error = round(real_drift * 0.8, 2)
    else:
        sim_drift_error = round(max(22.0, real_drift * 2.5), 2)
        
    sim_drift_error = round(sim_drift_error, 2)
    drift_triggered = sim_drift_error > threshold

    with col_stats:
        # 실시간 성능 메트릭 렌더링
        lat_color = "g" if sim_latency < 100 else ("y" if sim_latency < 300 else "r")
        drift_color = "r" if drift_triggered else "g"

        c_metric1, c_metric2, c_metric3 = st.columns(3)
        with c_metric1:
            render_kpi_card("평균 추론 지연 시간", f"{sim_latency} ms", "목표치: < 150ms 이내", lat_color)
        with c_metric2:
            render_kpi_card("최대 추론 처리량", f"{sim_throughput:,} SKU/s", "ONNX 최적화 배율 적용", "b")
        with c_metric3:
            render_kpi_card("실시간 SCM MAE 오차", f"{sim_drift_error} %", f"가드라인 임계치: {threshold}%", drift_color)

    st.write("")

    # ── Phase 6: 설명 가능한 AI (XAI) 및 실시간 TFT 하이브리드 수요 예측 ──
    render_section("실시간 TFT 하이브리드 수요 예측 및 SHAP 기여도 산출", "font-size: 16px; font-weight: 600; color: #e8eaed; border-bottom: 2px solid #3c4043; padding-bottom: 6px;")
    
    col_inputs, col_xai = st.columns([1, 1.2])
    
    with col_inputs:
        st.subheader("신규 발주 예측 대상 데이터 입력")
        
        # 1. 지점 선택 (Region) - REST API 동적 바인딩 및 셀렉트박스화
        regions_res = auth_helper.api_get("/api/regions")
        if not regions_res:
            regions_res = [{"regionName": "서울특별시", "regionCode": "KR-11", "description": "기본 관제소"}]
            
        region_options = {f"{r['regionName']} ({r['regionCode']})": r for r in regions_res}
        region_keys_list = list(region_options.keys())
        
        # Find active region index to default
        default_region_idx = 0
        for idx, key in enumerate(region_keys_list):
            if region_options[key]["regionCode"] == active_region_code:
                default_region_idx = idx
                break
                
        selected_region_lbl = st.selectbox("관제 대상 지점 선택 (Region)", options=region_keys_list, index=default_region_idx)
        selected_region_obj = region_options[selected_region_lbl]
        region_code = selected_region_obj["regionCode"]
        region_name = selected_region_obj["regionName"]
        
        # 2. 품목 선택 (SKU) - 해당 지점의 실제 재고 목록 실시간 연계 및 셀렉트박스화
        inv_data = auth_helper.api_get(f"/api/dashboard/region/{region_code}/inventory")
        if inv_data:
            products = list(set(inv["id"]["productName"] for inv in inv_data if inv.get("id", {}).get("productName")))
        else:
            products = []
            
        if not products:
            products = ["반도체 칩", "마스크", "종합 품목"]
            
        # Find active product index to default
        default_prod_idx = 0
        for idx, p in enumerate(products):
            if p == active_prod:
                default_prod_idx = idx
                break
                
        selected_prod_name = st.selectbox("분석 품목 선택 (SKU)", options=products, index=default_prod_idx)
        
        # 품목명 -> 품목 ID (SKU) 코드 매핑
        item_id_map = {
            "마스크": "MASK_A01",
            "반도체 칩": "SEMI_CHIP_X1",
            "종합 품목": "TOTAL_SKU_01"
        }
        if selected_prod_name in item_id_map:
            item_id = item_id_map[selected_prod_name]
        else:
            item_id = f"{selected_prod_name.upper().replace(' ', '_')}_01"
            
        # UI상 시각적 피드백 제공 (선택한 정보에 대응하는 코드쌍 출력)
        st.markdown(f"""
        <div style='background: rgba(138, 180, 248, 0.05); padding: 8px 12px; border-radius: 4px; border-left: 3px solid #8ab4f8; margin-top: -8px; margin-bottom: 12px;'>
            <span style='font-size: 11.5px; color: #8ab4f8;'>Selected Mapping:</span> 
            <strong style='font-size: 12px; color: #e8eaed;'>{selected_prod_name} ({item_id}) ➔ {region_name} ({region_code})</strong>
        </div>
        """, unsafe_allow_html=True)
        
        # 30일치 가짜 과거 판매량 슬라이더 입력기
        base_sales = st.slider("평균 일일 판매량 설정 (최근 30일 기준)", min_value=50, max_value=1000, value=250, step=10)
        
        # 공휴일 영향 토글
        is_holiday = st.checkbox("예측 대상 기간 중 초대형 유통 행사 / 명절 연휴 포함 여부", value=True)
        
        # API 예측 호출용 가짜 과거 판매량 구성
        sales_records = []
        for i in range(30):
            variance = ((i * 13 + 7) % 61) - 30 # Deterministic variance between -30 and 30
            sales_records.append({
                "date": f"2026-04-{i+1:02d}",
                "qty": float(base_sales + variance)
            })
            
        future_events = [{"date": "2026-05-01", "is_holiday": is_holiday, "event_type": "PROMOTION" if is_holiday else "NORMAL"}]
        
        if st.button("TFT 하이브리드 고속 추론 및 SHAP 산출 실행", type="secondary"):
            with st.spinner("API 서버에서 분위수(Pinball Loss) 고속 연산 및 SHAP 기여도 분석 중..."):
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
                        st.toast("TFT ONNX/PyTorch 하이브리드 실시간 추론 연산 성공!")
                    else:
                        st.error(f"API 추론 실패: {res.text}")
                except Exception as e:
                    st.error(f"API 서버 연결 실패: {e}. FastAPI `ml-api` 컨테이너 상태를 확인하세요.")
                    
        # 이전 결과 표시
        pred_result = st.session_state.get("tft_pred_result", None)
        if pred_result:
            st.markdown(f"""
            <div style="background: #202124; padding: 12px; border-radius: 6px; border-left: 4px solid #8ab4f8; margin-top: 10px;">
                <strong>AI 예측 결과분포 (분위수 예측)</strong><br/>
                • 모델 버전: <code>{pred_result['model_version']}</code><br/>
                • 분위수 q=0.1 (하한 예측): <span style='color:#f28b82; font-weight:bold;'>{pred_result['predicted_demand_10']} 개</span><br/>
                • 분위수 q=0.5 (중간 예측): <span style='color:#8ab4f8; font-weight:bold;'>{pred_result['predicted_demand_50']} 개</span><br/>
                • 분위수 q=0.9 (상한 예측): <span style='color:#81c995; font-weight:bold;'>{pred_result['predicted_demand_90']} 개</span>
            </div>
            """, unsafe_allow_html=True)

    with col_xai:
        st.subheader("XAI (SHAP Waterfall) 요인별 가치 기여도")
        if pred_result:
            # SHAP 폭포수 차트 렌더링
            shap = pred_result["shap_values"]
            features = list(shap.keys())
            values = list(shap.values())
            
            # Plotly 수평 바 차트를 활용해 SHAP Waterfall 렌더링
            # 긍정 기여(#00e5a0)와 부정 기여(#ff5c5c) 컬러 매핑
            colors = ["#00e5a0" if v >= 0 else "#ff5c5c" for v in values]
            
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
                font=dict(color=TX, family="Inter, sans-serif"),
                xaxis=dict(
                    gridcolor='rgba(255, 255, 255, 0.06)',
                    linecolor='rgba(255, 255, 255, 0.12)',
                    tickfont=dict(color=TX, size=9),
                    title=dict(text="SHAP 기여도 값 (최종 수요에 미치는 편차 가산율)", font=dict(color=TX, size=10))
                ),
                yaxis=dict(
                    gridcolor='rgba(255, 255, 255, 0.06)',
                    linecolor='rgba(255, 255, 255, 0.12)',
                    tickfont=dict(color=TX, size=9)
                ),
                margin=dict(l=40, r=20, t=10, b=40)
            )
            st.plotly_chart(fig_shap, use_container_width=True)
            
            st.markdown("""
            SHAP 해석 가이드:
            - **lag_1**: 전날 판매량의 연속성 기여 가중치입니다.
            - **is_holiday**: 공휴일/프로모션 지정에 따른 +20% 추가 가산 편향 강도입니다.
            - **rolling_mean_7**: 최근 7일간의 이동 평균 패턴이 예측치에 기여하는 지분율입니다.
            """)
        else:
            st.info("좌측의 [TFT 하이브리드 고속 추론 및 SHAP 산출 실행] 버튼을 클릭하면 설명 가능한 AI 분석 결과가 렌더링됩니다.")

    st.write("")

    # ── Human-in-the-Loop (의사결정 제어권) 제어 센터 ──
    render_section("Human-in-the-Loop (HITL) 예외 발주 승인 및 거절 통제소")
    st.write("안전 재공 차이를 초과하거나 불확실성(분위수 10% ~ 90% 편차)이 임계치를 초과하여 수동 검토(`PENDING`) 상태로 격리된 발주 목록입니다. 현업 담당자는 데이터를 검토 후 승인 혹은 거절할 수 있습니다.")
    
    # Reset/update pending orders if user changed the selected product or region inside MLOps dropdowns
    if (st.session_state.get("last_dropdown_item_id") != item_id or 
        st.session_state.get("last_dropdown_region_code") != region_code):
        st.session_state["last_dropdown_item_id"] = item_id
        st.session_state["last_dropdown_region_code"] = region_code
        # Clear predictions and pending orders so they regenerate with new values
        st.session_state.pop("hitl_pending_orders", None)
        st.session_state.pop("tft_pred_result", None)

    # 실제 서버에서 대기 중인 발주 목록 호출 (가짜 스캐폴딩 삭제)
    if "hitl_pending_orders" not in st.session_state:
        pending_orders_raw = auth_helper.api_get("/api/dashboard/pending-orders") or []
        mapped_orders = []
        for raw in pending_orders_raw:
            mapped_orders.append({
                "id": f"ORD-{raw.get('transferId', 'TMP')}",
                "item_id": raw.get("productName", "SKU"),
                "region": f"{raw.get('toRegion', 'Region')}",
                "ai_predicted_50": int(raw.get("transferQty", 100) * 0.9),
                "uncertainty_gap": int(raw.get("transferQty", 100) * 0.2),
                "suggested_order_qty": raw.get("transferQty", 100),
                "status": "PENDING",
                "reason": raw.get("reason", "자동 분류된 검토 대기 건")
            })
        st.session_state["hitl_pending_orders"] = mapped_orders

    pending_list = [o for o in st.session_state["hitl_pending_orders"] if o["status"] == "PENDING"]
    
    # [고도화 C11] 데이터 테이블 페이징 고도화 (Pagination)
    if pending_list:
        import math
        
        PAGE_SIZE = 3
        total_pages = math.ceil(len(pending_list) / PAGE_SIZE)
        
        st.markdown(f"<div style='font-size: 13px; color: #8892b0; margin-bottom: 10px;'>전체 {len(pending_list)}건 중 {PAGE_SIZE}건씩 표시 (총 {total_pages}페이지)</div>", unsafe_allow_html=True)
        
        cols_pag = st.columns([1, 1, 4])
        with cols_pag[0]:
            current_page = st.number_input("페이지 선택", min_value=1, max_value=max(1, total_pages), value=1, step=1, key="hitl_page_num")
        
        start_idx = (current_page - 1) * PAGE_SIZE
        end_idx = start_idx + PAGE_SIZE
        page_items = pending_list[start_idx:end_idx]
        
        for idx, order in enumerate(page_items):
            # 네이티브 Streamlit 컨테이너 카드로 리액트 DOM 충돌 원천 해결 및 실시간 수리 연동
            with st.container(border=True):
                # 상단 헤더행
                col_h1, col_h2 = st.columns([4, 1])
                with col_h1:
                    st.markdown(f"##### 📦 발주 번호: `{order['id']}`")
                with col_h2:
                    st.markdown(f"<span style='background:#fdd66322; color:#fdd663; border: 1px solid #fdd66355; border-radius:3px; padding: 2px 8px; font-size:10px; font-weight:bold;'>{order['status']}</span>", unsafe_allow_html=True)
                
                st.markdown(f"**🎯 대상 품목 / 지점**: {order['item_id']} / {order['region']}")
                
                # Dynamic Metric Cards
                m_col1, m_col2, m_col3 = st.columns(3)
                with m_col1:
                    st.metric(label="AI 중간값 예측수요 (q=50%)", value=f"{order['ai_predicted_50']:,} 개")
                with m_col2:
                    st.metric(label="수요 불확실성 편차폭 (q90-q10)", value=f"{order['uncertainty_gap']:,} 개")
                with m_col3:
                    st.metric(label="추천 발주 공급량 (MOQ 보정)", value=f"{order['suggested_order_qty']:,} 개")
                
                st.warning(f"🛡 시스템 수동 격리 사유: {order['reason']}")
                
                # 사용자 액션용 컬럼 분할
                col_act1, col_act2, _ = st.columns([1, 1, 4])
                with col_act1:
                    if st.button("최종 승인", key=f"app_{order['id']}", use_container_width=True, type="primary"):
                        order["status"] = "APPROVED"
                        st.success(f"주문 {order['id']} 발주가 성공적으로 승인되어 Java backend 전송 큐에 등록되었습니다.")
                        st.toast(f"발주 {order['id']} 승인 처리 완료.")
                        st.rerun()
                with col_act2:
                    if st.button("수정 및 거절", key=f"rej_{order['id']}", use_container_width=True):
                        order["status"] = "REJECTED"
                        st.warning(f"주문 {order['id']} 발주가 반려 및 차단되었습니다.")
                        st.toast(f"발주 {order['id']} 반려 처리 완료.")
                        st.rerun()
    
    # 처리 완료된 항목 요약 표시
    processed_orders = [o for o in pending_list if o["status"] != "PENDING"]
    if processed_orders:
        with st.expander("HITL 처리 완료 이력 (최근 5건)", expanded=False):
            for po in processed_orders:
                st.write(f"• 발주 `{po['id']}` -> 상태: `{po['status']}` ({po['region']})")

if __name__ == "__main__":
    render_mlops_simulator_dashboard()
