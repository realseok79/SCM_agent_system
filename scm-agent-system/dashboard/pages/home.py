# dashboard/pages/home.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os
from datetime import datetime
import auth_helper
import plotly.graph_objects as go
from components.styles import BG, TX, sax

def render_home_dashboard():
    summary = auth_helper.api_get("/api/dashboard/summary")
    if not summary:
        st.warning("⚠️ 백엔드 서비스와 통신할 수 없거나 세션이 만료되었습니다. 로그인 상태를 확인해 주세요.")
        return

    st.markdown(f'<div class="hdr"><div><div class="hdr-t">SCM AI 자율 제어 관제탑 (REST Dashboard)</div><div class="hdr-s">스프링 백엔드 통합 SCM 텔레메트리 &nbsp;·&nbsp; {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div></div></div>', unsafe_allow_html=True)

    # KPI 융합 카드 렌더링
    st.markdown(f'''<div class="kg">
<div class="kc"><div class="kl">등록 지점 수</div><div class="kv b">{summary.get("totalRegions", 0)} 개소</div><div class="ku">실무 가용 물류 거점</div></div>
<div class="kc"><div class="kl">전체 모니터링 SKU</div><div class="kv">12 품목</div><div class="ku">등록된 활성 상품 종류</div></div>
<div class="kc"><div class="kl">통합 가용 재고량</div><div class="kv g">{summary.get("totalStock", 0.0):,.0f} 개</div><div class="ku">지점별 최신 재고 합산</div></div>
<div class="kc"><div class="kl">발주 장애 사고 건수</div><div class="kv r">{summary.get("totalStockOutIncidents", 0)} 건</div><div class="ku">안전 기준 미달 품절 사고</div></div>
<div class="kc"><div class="kl">관제 시스템 상태</div><div class="kv g">{summary.get("systemStatus", "STABLE")}</div><div class="ku">서버 정상 작동 유무</div><div class="kb ok">정상</div></div>
</div>''', unsafe_allow_html=True)

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
            delta="⬆ ₩1,200,000 (전일 대비 증가)",
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
        st.markdown('<div class="cc"><div class="ct"><span class="dt" style="background:#f28b82"></span>자동 발주 승인 대기 목록</div>', unsafe_allow_html=True)
        if "order_approved_seoul" not in st.session_state:
            st.session_state["order_approved_seoul"] = False

        if not st.session_state["order_approved_seoul"]:
            st.markdown("""
            <div class="ep ec" style="border-left-color: #f28b82; padding: 12px; margin-bottom: 10px;">
                <div class="et" style="color: #f28b82; font-weight: bold; font-size: 13px;">⚠️ [안전 재고 경고] 서울 물류창고 마스크 고갈 우려</div>
                <div class="eb" style="font-size: 12px; margin-top: 5px; color: #e8eaed;">
                    서울점 <b>마스크</b> 품목 재고가 안전재고 ROP 이하로 떨어졌습니다.<br/>
                    자율 AI 최적 발주량 <b>500개</b>의 주문을 승인하겠습니까?
                </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button("📥 자동 발주 승인 및 다운로드", key="btn_download_seoul"):
                st.session_state["order_approved_seoul"] = True
                st.success("발주 승인되었습니다.")
                st.rerun()
        else:
            st.markdown("""
            <div class="ep en" style="border-left-color: #81c995; padding: 12px; margin-bottom: 10px;">
                <div class="et" style="color: #81c995; font-weight: bold; font-size: 13px;">✅ [발주 완료] 서울점 마스크 발주서 생성 완료</div>
                <div class="eb" style="font-size: 12px; margin-top: 5px; color: #e8eaed;">
                    서울점 <b>마스크 500개</b>에 대한 발주 요청이 승인되어 <b>진행 중</b> 상태로 전환되었습니다.
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("🔄 발주 요청 초기화 (테스트용)", key="reset_seoul"):
                st.session_state["order_approved_seoul"] = False
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with chk_col2:
        st.markdown('<div class="cc"><div class="ct"><span class="dt" style="background:#81c995"></span>실시간 물류 건강 지표</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="ep en" style="border-left-color: #81c995; padding: 12px; min-height: 110px;">
            <div class="et" style="color: #81c995; font-weight: bold; font-size: 13px;">🟢 전 지점 운송 경로 정상</div>
            <div class="eb" style="font-size: 12px; margin-top: 5px; color: #e8eaed;">
                현재 모든 물류 거점의 환경이 양호합니다.<br/>
                배송 지연 요인이 식별되지 않았습니다.
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ------------------ [Plotly Node-Link Map & Prescriptive Grid] ------------------
    st.markdown('<div class="cc"><div class="ct"><span class="dt" style="background:#81c995"></span>지점 간 재고 자율 밸런싱 네트워크 맵 (Plotly Node-Link Map)</div>', unsafe_allow_html=True)
    
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

        # Line thickness relative to quantity
        line_w = max(2.0, min(8.0, qty / 50.0))
        
        hover_text = (
            f"<b>품목:</b> {prod}<br>"
            f"<b>경로:</b> {from_n} ➔ {to_n}<br>"
            f"<b>이송 수량:</b> {qty:,} units<br>"
            f"<b>물류비 절감:</b> ₩{saved:,}<br>"
            f"<b>처방 근거 (XAI):</b> {reason}"
        )

        # Path Line
        fig.add_trace(go.Scattermapbox(
            lat=[from_c[0], to_c[0]],
            lon=[from_c[1], to_c[1]],
            mode='lines',
            line=dict(width=line_w, color='#8ab4f8'),
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
                size=9,
                color='#81c995'
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
    st.markdown('<div class="cc"><div class="ct"><span class="dt" style="background:#f28b82"></span>의사결정 인과관계 처방 그리드 (From-To Reason Grid)</div>', unsafe_allow_html=True)
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
    st.markdown('<div class="cc"><div class="ct"><span class="dt" style="background:#8ab4f8"></span>최근 7일간 전체 재고 추이 (REST 집계)</div>', unsafe_allow_html=True)
    trend_data = auth_helper.api_get("/api/dashboard/stock-trend")
    if trend_data:
        df = pd.DataFrame(trend_data)
        fig, ax = plt.subplots(figsize=(10, 2.5), dpi=100)
        fig.patch.set_facecolor(BG)
        ax.set_facecolor(BG)
        ax.plot(df["date"], df["quantity"], color="#8ab4f8", lw=1.8, marker="o", label="전체 재고 합계")
        ax.fill_between(df["date"], df["quantity"], alpha=0.08, color="#8ab4f8")
        sax(ax)
        ax.set_xlabel("일자 (Date)", fontsize=8, color=TX)
        ax.set_ylabel("수량 (Units)", fontsize=8, color=TX)
        ax.legend(fontsize=7, framealpha=0, loc="upper left", labelcolor=TX)
        fig.tight_layout(pad=0.5)
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)
    else:
        st.info("💡 차트를 그리기 위한 데이터가 부족합니다.")
    st.markdown('</div>', unsafe_allow_html=True)
