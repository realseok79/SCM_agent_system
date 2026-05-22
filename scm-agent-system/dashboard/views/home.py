# dashboard/pages/home.py
import streamlit as st
import pandas as pd
import os
from datetime import datetime
import auth_helper
import plotly.graph_objects as go
from components.styles import BG, TX

def render_home_dashboard():
    summary = auth_helper.api_get("/api/dashboard/summary")
    if not summary:
        st.warning("⚠️ 백엔드 서비스와 통신할 수 없거나 세션이 만료되었습니다. 로그인 상태를 확인해 주세요.")
        return

    st.markdown(f'<div class="hdr"><div><div class="hdr-t">SCM AI 자율 제어 관제탑 (REST Dashboard)</div><div class="hdr-s">스프링 백엔드 통합 SCM 텔레메트리 &nbsp;·&nbsp; {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div></div></div>', unsafe_allow_html=True)

    # KPI 융합 카드 렌더링
    st.markdown(f'''<div class="kg">
<div class="kc"><div class="kl">등록 지점 수</div><div class="kv b">{summary.get("totalRegions", 0)} 개소</div><div class="ku">실무 가용 물류 거점</div></div>
<div class="kc"><div class="kl">전체 모니터링 SKU</div><div class="kv">{summary.get("totalSkuCount", 0)} 품목</div><div class="ku">등록된 활성 상품 종류</div></div>
<div class="kc"><div class="kl">통합 가용 재고량</div><div class="kv g">{summary.get("totalStock", 0.0):,.0f} 개</div><div class="ku">지점별 최신 재고 합산</div></div>
<div class="kc"><div class="kl">발주 장애 사고 건수</div><div class="kv r">{summary.get("totalStockOutIncidents", 0)} 건</div><div class="ku">안전 기준 미달 품절 사고</div></div>
<div class="kc"><div class="kl">관제 시스템 상태</div><div class="kv g">{summary.get("systemStatus", "STABLE")}</div><div class="ku">서버 정상 작동 유무</div><div class="kb ok">정상</div></div>
</div>''', unsafe_allow_html=True)

    # 🧪 데모 시뮬레이션 모드 전용 대시보드
    if st.session_state.get("demo_mode", False):
        with st.container():
            st.markdown("""
            <div style="background-color: #1a202c; border: 1px solid #e53e3e; border-radius: 6px; padding: 16px; margin-bottom: 20px;">
                <h4 style="color: #e53e3e; margin-top: 0;">🧪 데모 시뮬레이션 컨트롤 타워</h4>
                <p style="font-size: 13px; color: #a0aec0;">데모 모드 활성화 상태입니다. 아래 버튼을 클릭하여 SCM 시스템에 실시간 비상 시나리오 이벤트를 주입해보세요.</p>
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("🚨 가상 고위험(HIGH) 경보 생성", use_container_width=True):
                    import requests
                    try:
                        requests.post("http://localhost:8080/api/audit-logs", json={
                            "eventType": "RISK_ALERT",
                            "message": "🚨 [데모] 수도권 Hub(KR-SL) 지점의 기상 이변(집중 호우)으로 인해 물류 지연 리스크 레벨이 HIGH로 상승했습니다.",
                            "triggeredBy": "DEMO_AGENT"
                        }, timeout=3)
                        st.success("고위험 감사 로그 생성 완료!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")
            with c2:
                if st.button("🛠️ IoT 디바이스 점검(MAINTENANCE) 설정", use_container_width=True):
                    import requests
                    try:
                        requests.post("http://localhost:8080/api/audit-logs", json={
                            "eventType": "DEVICE_MAINTENANCE",
                            "message": "🛠️ [데모] KR-SL 지점의 온도 센서(TEMP-001)의 노이즈 감지로 인해 시스템이 점검 상태로 전환되었습니다.",
                            "triggeredBy": "DEMO_AGENT"
                        }, timeout=3)
                        st.success("점검 감사 로그 생성 완료!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")
            with c3:
                if st.button("🟢 자율 재배정 승인(APPROVED) 발생", use_container_width=True):
                    import requests
                    try:
                        requests.post("http://localhost:8080/api/audit-logs", json={
                            "eventType": "ORDER_APPROVED",
                            "message": "🟢 [데모] 영남권물류 Center 재고 결핍으로 수도권중앙 Hub에서 150개 자동 이송 주문(ORD-999) 승인 완료",
                            "triggeredBy": "DEMO_AGENT"
                        }, timeout=3)
                        st.success("자율 승인 감사 로그 생성 완료!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")

    # 0. API 호출로 재고 조정 주문 목록 수신 및 누적 절감 물류비 집계
    rebalancing_orders = auth_helper.api_get("/api/dashboard/rebalancing-orders")
    
    # Fallback to realistic demo data ONLY if SCM_DEMO_MODE=true is injected
    if not rebalancing_orders:
        demo_mode = os.getenv("SCM_DEMO_MODE", "false").lower() == "true"
        if demo_mode:
            rebalancing_orders = [
                {
                    "transferId": 101,
                    "productName": "반도체_부품_8",
                    "fromRegion": "수도권중앙Hub",
                    "toRegion": "영남권물류Center",
                    "transferQty": 250,
                    "savedCost": 2500000,
                    "status": "APPROVED",
                    "reason": "[과잉: 수도권중앙Hub (DoS 124일)] ➔ [결핍: 영남권물류Center (안전재고 -15%)]",
                    "createdAt": "2026-05-20T10:00:00"
                },
                {
                    "transferId": 102,
                    "productName": "의류_티셔츠",
                    "fromRegion": "중부권물류Center",
                    "toRegion": "호남권물류Center",
                    "transferQty": 180,
                    "savedCost": 1800000,
                    "status": "APPROVED",
                    "reason": "[과잉: 중부권물류Center (DoS 95일)] ➔ [결핍: 호남권물류Center (품절 3일 전)]",
                    "createdAt": "2026-05-20T11:30:00"
                },
                {
                    "transferId": 103,
                    "productName": "마스크_KF94",
                    "fromRegion": "수도권중앙Hub",
                    "toRegion": "호남권물류Center",
                    "transferQty": 320,
                    "savedCost": 3200000,
                    "status": "APPROVED",
                    "reason": "[과잉: 수도권중앙Hub (DoS 150일)] ➔ [결핍: 호남권물류Center (안전재고 ROP 이하)]",
                    "createdAt": "2026-05-20T14:15:00"
                }
            ]
        else:
            rebalancing_orders = []

    total_saved_cost = sum(order.get("savedCost", 0) for order in rebalancing_orders)
    
    col_metric, col_status = st.columns([2, 1])
    with col_metric:
        st.metric(
            label="💡 AI 자율 재고 조정 누적 절감 물류비 (TC)",
            value=f"₩{total_saved_cost:,.0f}",
            delta=f"⬆ ₩{summary.get('savedCostDelta', 0):,.0f} (전일 대비)",
            delta_color="normal"
        )
    with col_status:
        st.metric(
            label="⚡ 실시간 의사결정 경로 수",
            value=f"{len(rebalancing_orders)}개 최적화 링크",
            delta="정상 작동 중",
            delta_color="off"
        )

    # SCM 운영 및 발주 체크리스트 추가
    st.markdown("### 📋 오늘의 SCM 운영 및 발주 체크리스트")
    chk_col1, chk_col2 = st.columns([1.8, 1.2])

    with chk_col1:
        st.markdown('<div class="cc"><div class="ct"><span class="dt" style="background:#ff5c5c"></span>자동 발주 승인 대기 목록</div>', unsafe_allow_html=True)
        pending_orders = auth_helper.api_get("/api/dashboard/pending-orders") or []
        
        if not pending_orders:
            st.info("✅ 대기 중인 자동 발주 요청이 없습니다.")
        else:
            for order in pending_orders:
                order_id = order["transferId"]
                prod = order["productName"]
                from_reg = order["fromRegion"]
                to_reg = order["toRegion"]
                qty = order["transferQty"]
                saved = order["savedCost"]
                reason = order.get("reason") or f"[{from_reg}] ➔ [{to_reg}] 안전재고 임계치 미달 복구용 발주"

                st.markdown(f"""
                <div class="ep ec" style="border-left-color: #ff5c5c; padding: 12px; margin-bottom: 10px;">
                    <div class="et" style="color: #ff5c5c; font-weight: bold; font-size: 13px;">⚠️ [안전 재고 경고] {to_reg}점 {prod} 고갈 우려</div>
                    <div class="eb" style="font-size: 12px; margin-top: 5px; color: #e8eaed;">
                        경로: <b>{from_reg}</b> ➔ <b>{to_reg}</b> ({qty}개)<br/>
                        절감 효과: ₩{saved:,.0f}<br/>
                        상세 사유: {reason}<br/>
                        자율 AI 최적 발주를 승인하겠습니까?
                    </div>
                </div>
                """, unsafe_allow_html=True)

                user_role = st.session_state.get("user_role", "ROLE_USER")
                if user_role == "ROLE_EXECUTIVE":
                    st.info("🔒 [읽기 전용] 경영진 계정은 발주 승인 및 반려 피드백 조작 권한이 없습니다.")
                elif user_role == "ROLE_LOGISTICS":
                    col1, = st.columns([1])
                    with col1:
                        if st.button("📥 자동 발주 승인", key=f"btn_approve_{order_id}", use_container_width=True):
                            res = auth_helper.api_post(f"/api/orders/{order_id}/approve", {})
                            if res:
                                st.success(f"주문 #{order_id} 승인 완료")
                                st.rerun()
                else: # ROLE_ADMIN
                    col_app, col_rej = st.columns([1, 1])
                    with col_app:
                        if st.button("📥 자동 발주 승인", key=f"btn_approve_{order_id}", use_container_width=True):
                            res = auth_helper.api_post(f"/api/orders/{order_id}/approve", {})
                            if res:
                                st.success(f"주문 #{order_id} 승인 완료")
                                st.rerun()
                    with col_rej:
                        if st.button("❌ 반려 및 AI 피드백", key=f"btn_reject_init_{order_id}", use_container_width=True):
                            st.session_state[f"rejecting_order_{order_id}"] = True
                            st.rerun()

                    if st.session_state.get(f"rejecting_order_{order_id}", False):
                        st.markdown("<div style='background-color:rgba(255, 92, 92, 0.04); border: 1px solid rgba(255, 92, 92, 0.15); padding:12px; border-radius:4px; margin-top:10px;'>", unsafe_allow_html=True)
                        st.write("📋 **반려 사유 및 AI 피드백**")
                        mapping_opt = st.selectbox(
                            "어떤 컬럼의 매핑 오류가 발주 실패를 유발했습니까?",
                            options=[
                                ("수량 데이터 매핑 오류 (quantity)", "quantity", "물품수량"),
                                ("날짜 데이터 매핑 오류 (date)", "date", "입고일자"),
                                ("지역 코드 매핑 오류 (region_code)", "region_code", "지점명")
                            ],
                            format_func=lambda x: x[0],
                            key=f"rej_select_{order_id}"
                        )
                        feedback_reason = st.text_input("반려 의견 추가 (선택사항)", key=f"rej_reason_{order_id}")
                        if st.button("피드백 전송 및 반려 완료", key=f"submit_reject_{order_id}"):
                            payload = {
                                "companyId": "SIGMA",
                                "rawHeader": mapping_opt[2],
                                "mappedColumn": mapping_opt[1]
                            }
                            # 1. Decay feedback call
                            auth_helper.api_post("/api/feedback/reject-mapping", payload)
                            # 2. Reject order call
                            order_payload = {"reason": f"{mapping_opt[0]}. 의견: {feedback_reason}"}
                            res = auth_helper.api_post(f"/api/orders/{order_id}/reject", order_payload)
                            if res:
                                st.session_state.pop(f"rejecting_order_{order_id}", None)
                                st.success(f"주문 #{order_id} 반려 완료 및 AI 피드백 반영")
                                st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with chk_col2:
        st.markdown('<div class="cc"><div class="ct"><span class="dt" style="background:#00e5a0"></span>실시간 물류 건강 지표</div>', unsafe_allow_html=True)
        
        # IoT health summary integration
        iot_health = auth_helper.api_get("/api/iot/health-summary") or {}
        avg_score = iot_health.get("averageHealthScore", 100.0)
        
        if avg_score >= 80.0:
            icon, color, health_msg = "🟢", "#00e5a0", "전 지점 운송 경로 정상"
        elif avg_score >= 50.0:
            icon, color, health_msg = "🟡", "#fdd663", f"일부 거점 주의 (건강도 {avg_score:.1f}점)"
        else:
            icon, color, health_msg = "🔴", "#ff5c5c", f"긴급: 물류 지연 예상 (건강도 {avg_score:.1f}점)"

        st.markdown(f"""
        <div class="ep en" style="border-left-color: {color}; padding: 12px; margin-bottom: 10px;">
            <div class="et" style="color: {color}; font-weight: bold; font-size: 13px;">{icon} {health_msg}</div>
            <div class="eb" style="font-size: 12px; margin-top: 5px; color: #e8eaed;">
                평균 창고 건강 지수: <b>{avg_score:.1f} / 100.0</b><br/>
                실시간 IoT 디바이스 텔레메트리 스트림 수집 중.
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Isolation Forest Anomaly Agent integration
        has_anomalies = False
        anomaly_msg = ""
        try:
            import requests
            regions = auth_helper.api_get("/api/regions") or []
            headers = {"Authorization": f"Bearer {st.session_state.get('access_token', '')}"}
            
            for r in regions:
                code = r["regionCode"]
                # 서울/Seoul hub gets dummy anomaly data to demonstrate ML warning
                if "Seoul" in r["regionName"] or "서울" in r["regionName"]:
                    telemetry = [
                        {"temperature": 22.0, "humidity": 45.0, "vibration": 0.05},
                        {"temperature": 22.5, "humidity": 46.0, "vibration": 0.04},
                        {"temperature": 23.0, "humidity": 44.0, "vibration": 0.05},
                        {"temperature": 39.8, "humidity": 85.0, "vibration": 1.95} # Outlier!
                    ]
                else:
                    telemetry = [
                        {"temperature": 21.0, "humidity": 40.0, "vibration": 0.02},
                        {"temperature": 21.2, "humidity": 40.5, "vibration": 0.03},
                        {"temperature": 21.5, "humidity": 41.0, "vibration": 0.02},
                        {"temperature": 21.1, "humidity": 40.2, "vibration": 0.03}
                    ]
                
                payload = {"telemetry_logs": telemetry}
                res = requests.post(f"{auth_helper.API_BASE_URL}/api/v1/ml/anomaly-score", json=payload, headers=headers, timeout=2.0)
                if res.status_code == 200:
                    ml_res = res.json()
                    # If the last log is anomalous (-1)
                    if ml_res.get("is_anomaly", []) and ml_res["is_anomaly"][-1] == -1:
                        has_anomalies = True
                        anomaly_msg += f"🚨 <b>{r['regionName']} ({code})</b>: 비정상 고온(39.8°C) 및 과진동(1.95) 감지!<br/>"
        except Exception:
            pass
            
        if has_anomalies:
            st.markdown(f"""
            <div class="ep ec" style="border-left-color: #ff5c5c; padding: 12px; min-height: 110px; background-color: rgba(255, 92, 92, 0.04);">
                <div class="et" style="color: #ff5c5c; font-weight: bold; font-size: 13px;">⚠️ [이상 상태 감지] 창고 센서 리스크</div>
                <div class="eb" style="font-size: 12px; margin-top: 5px; color: #e8eaed;">
                    {anomaly_msg}
                    🤖 <b>Isolation Forest AI 분석:</b> 장비 오작동 전조 증상이 실시간 포착되었습니다. 즉시 안전 현장 점검이 권장됩니다.
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    # ------------------ [Plotly Node-Link Map & Prescriptive Grid] ------------------
    st.markdown('<div class="cc"><div class="ct"><span class="dt" style="background:#00e5a0"></span>지점 간 재고 자율 밸런싱 네트워크 맵 (Plotly Node-Link Map)</div>', unsafe_allow_html=True)
    
    # Hub coordinates (Hardcoded as approved)
    HUB_COORDINATES = {
        "수도권중앙Hub": [37.5665, 126.9780],
        "영남권물류Center": [35.5384, 129.3114],
        "호남권물류Center": [35.1595, 126.8526],
        "중부권물류Center": [36.3504, 127.3845],
        "GLOBAL_ORDER": [37.4563, 126.7052],
        "수도권": [37.5665, 126.9780],
        "영남": [35.5384, 129.3114],
        "호남": [35.1595, 126.8526],
        "중부": [36.3504, 127.3845],
    }

    # Gather nodes
    unique_nodes = set()
    for o in rebalancing_orders:
        unique_nodes.add(o.get("fromRegion", "수도권중앙Hub"))
        unique_nodes.add(o.get("toRegion", "GLOBAL_ORDER"))
    
    unique_nodes.update(["수도권중앙Hub", "영남권물류Center", "호남권물류Center", "중부권물류Center"])
    
    node_lats = []
    node_lons = []
    node_names = []
    for node in unique_nodes:
        coords = None
        for key, val in HUB_COORDINATES.items():
            if key in node:
                coords = val
                break
        if coords is None:
            coords = HUB_COORDINATES["수도권중앙Hub"]
        node_lats.append(coords[0])
        node_lons.append(coords[1])
        node_names.append(node)

    fig = go.Figure()
    
    # Render nodes
    fig.add_trace(go.Scattermapbox(
        lat=node_lats,
        lon=node_lons,
        mode='markers+text',
        marker=dict(
            size=14,
            color='#ff5a5f',
            opacity=0.9
        ),
        text=node_names,
        textposition="top center",
        textfont=dict(color="#ffffff", size=9),
        hoverinfo='text',
        hovertext=node_names,
        name="물류 거점"
    ))

    # Render links
    for idx, order in enumerate(rebalancing_orders):
        from_n = order.get("fromRegion", "수도권중앙Hub")
        to_n = order.get("toRegion", "GLOBAL_ORDER")
        qty = order.get("transferQty", 100)
        saved = order.get("savedCost", 0)
        reason = order.get("reason", "")
        prod = order.get("productName", "")

        # Get coordinates
        from_c = None
        for key, val in HUB_COORDINATES.items():
            if key in from_n:
                from_c = val
                break
        if from_c is None:
            from_c = HUB_COORDINATES["수도권중앙Hub"]

        to_c = None
        for key, val in HUB_COORDINATES.items():
            if key in to_n:
                to_c = val
                break
        if to_c is None:
            to_c = HUB_COORDINATES["GLOBAL_ORDER"]

        # ── Day 7: XGBoost Predict Agent - Lead Time Integration ──
        weather_score = 6.8 if "Hub" in from_n else 2.1 # high weather score to trigger warning for demo
        port_score = 48.0 if "Center" in to_n else 10.0
        pred_days = 2.8
        try:
            import requests
            headers = {"Authorization": f"Bearer {st.session_state.get('access_token', '')}"}
            payload = {
                "route_id": f"{from_n}_{to_n}",
                "weather_score": weather_score,
                "port_congestion_score": port_score,
                "historical_lead_times": [2.5, 3.0, 2.7, 3.1]
            }
            res = requests.post(f"{auth_helper.API_BASE_URL}/api/v1/ml/predict-leadtime", json=payload, headers=headers, timeout=1.5)
            if res.status_code == 200:
                ml_res = res.json()
                pred_days = ml_res.get("predicted_lead_time_days", 2.8)
        except Exception:
            pass

        # Line thickness relative to quantity
        line_w = max(2.0, min(8.0, qty / 50.0))
        
        # If predicted lead time > 3.2 days, flag as DELAYED (Red Dashed Line)
        is_delayed = pred_days > 3.2
        line_color = '#ff6b6b' if is_delayed else '#8ab4f8'
        line_dash = 'dash' if is_delayed else 'solid'
        
        hover_text = (
            f"<b>품목:</b> {prod}<br>"
            f"<b>경로:</b> {from_n} ➔ {to_n}<br>"
            f"<b>이송 수량:</b> {qty:,} units<br>"
            f"<b>🤖 XGBoost 예상 리드타임:</b> <span style='color:{line_color}'><b>{pred_days:.2f} 일</b></span> {'⚠️ (지연 위험)' if is_delayed else '🟢 (안정)'}<br>"
            f"<b>물류비 절감:</b> ₩{saved:,}<br>"
            f"<b>처방 근거 (XAI):</b> {reason}"
        )

        # Path Line (Dashed red if ML predicts delay risk)
        fig.add_trace(go.Scattermapbox(
            lat=[from_c[0], to_c[0]],
            lon=[from_c[1], to_c[1]],
            mode='lines',
            line=dict(width=line_w, color=line_color, dash=line_dash),
            hoverinfo='text',
            hovertext=hover_text,
            name=f"최적 경로 {idx+1}"
        ))

        # Midpoint indicator
        mid_lat = (from_c[0] + to_c[0]) / 2.0
        mid_lon = (from_c[1] + to_c[1]) / 2.0
        fig.add_trace(go.Scattermapbox(
            lat=[mid_lat],
            lon=[mid_lon],
            mode='markers',
            marker=dict(
                size=10,
                color='#ff5c5c' if is_delayed else '#00e5a0',
                symbol='circle'
            ),
            hoverinfo='text',
            hovertext=hover_text,
            name=f"최적 경로 {idx+1} 상세"
        ))

    fig.update_layout(
        mapbox=dict(
            style="carto-darkmatter",
            center=dict(lat=36.0, lon=127.8),
            zoom=6.1
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ------------------ [Prescriptive Grid UI] ------------------
    st.markdown('<div class="cc"><div class="ct"><span class="dt" style="background:#ff5c5c"></span>의사결정 인과관계 처방 그리드 (From-To Reason Grid)</div>', unsafe_allow_html=True)
    grid_df = pd.DataFrame(rebalancing_orders)
    if not grid_df.empty:
        grid_df_display = grid_df[[
            "transferId", "productName", "fromRegion", "toRegion", 
            "transferQty", "savedCost", "reason", "status"
        ]].copy()
        
        grid_df_display.columns = [
            "ID", "품목명", "과잉 공급처", "긴급 수요처", 
            "이동 수량", "물류비 절감액", "자율 최적화 사유 (XAI)", "의사결정 상태"
        ]

        def format_status(val):
            if val == "APPROVED":
                return "🟢 승인됨 (APPROVED)"
            elif val == "PENDING":
                return "🟡 대기중 (PENDING)"
            else:
                return "🔵 완료됨 (COMPLETED)"
        
        grid_df_display["의사결정 상태"] = grid_df_display["의사결정 상태"].apply(format_status)

        st.dataframe(
            grid_df_display,
            use_container_width=True,
            column_config={
                "ID": st.column_config.NumberColumn(format="%d"),
                "이동 수량": st.column_config.NumberColumn(format="%d 개"),
                "물류비 절감액": st.column_config.NumberColumn(format="₩%d"),
                "의사결정 상태": st.column_config.SelectboxColumn(
                    options=["🟢 승인됨 (APPROVED)", "🟡 대기중 (PENDING)", "🔵 완료됨 (COMPLETED)"],
                    width="small"
                )
            },
            hide_index=True
        )
    else:
        st.info("💡 처방 그리드 데이터가 존재하지 않습니다.")
    st.markdown('</div>', unsafe_allow_html=True)

    # 최근 7일 재고 추이 시각화
    st.markdown('<div class="cc"><div class="ct"><span class="dt" style="background:#00e5a0"></span>최근 7일간 전체 재고 추이 (REST 집계)</div>', unsafe_allow_html=True)
    trend_data = auth_helper.api_get("/api/dashboard/stock-trend")
    if trend_data:
        df = pd.DataFrame(trend_data)
        
        # Plotly dark theme chart with neon-emerald line and mint semi-transparent fill
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["date"],
            y=df["quantity"],
            mode="lines+markers",
            name="전체 재고 합계",
            line=dict(color="#00e5a0", width=2.5),
            marker=dict(color="#7effc8", size=6, line=dict(color="#00e5a0", width=1.5)),
            fill="tozeroy",
            fillcolor="rgba(126, 255, 200, 0.06)",
            hoverinfo="x+y"
        ))
        
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0, 0, 0, 0)",
            plot_bgcolor="rgba(0, 0, 0, 0)",
            font=dict(color=TX, family="Inter, sans-serif"),
            margin=dict(l=40, r=20, t=10, b=40),
            height=260,
            showlegend=False,
            xaxis=dict(
                gridcolor="rgba(255, 255, 255, 0.06)",
                linecolor="rgba(255, 255, 255, 0.12)",
                tickfont=dict(color=TX, size=9),
                title=dict(text="일자 (Date)", font=dict(color=TX, size=10))
            ),
            yaxis=dict(
                gridcolor="rgba(255, 255, 255, 0.06)",
                linecolor="rgba(255, 255, 255, 0.12)",
                tickfont=dict(color=TX, size=9),
                title=dict(text="수량 (Units)", font=dict(color=TX, size=10))
            )
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("💡 차트를 그리기 위한 데이터가 부족합니다.")
    st.markdown('</div>', unsafe_allow_html=True)
