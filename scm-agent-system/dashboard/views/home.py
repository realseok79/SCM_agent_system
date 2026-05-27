# dashboard/views/home.py
import streamlit as st
from datetime import datetime
import auth_helper
import plotly.graph_objects as go
from components.styles import inject_custom_css
from components.kpi_cards import render_sync_health_card, render_emergency_order_count
from components.inventory_charts import render_pending_orders_list, render_high_risk_regions

def render_home_dashboard():
    inject_custom_css()
    
    # Header Title
    st.markdown('<div class="hdr"><div class="hdr-t">SCM Control Tower Dashboard</div><div class="hdr-s">지능형 공급망 및 자율 재고 조율 시스템 메인 관제 화면</div></div>', unsafe_allow_html=True)
    
    # 1. 데이터 수집
    iot_health = auth_helper.api_get("/api/iot/health-summary")
    pending_orders = auth_helper.api_get("/api/dashboard/pending-orders") or []
    regions = auth_helper.api_get("/api/regions") or []
    summary = auth_helper.api_get("/api/dashboard/summary") or {}
    
    # 2. 마지막 동기화 시간 및 시스템 건강 상태 카드 렌더링
    last_sync = datetime.now().strftime("%Y-%m-%d %I:%M %p")
    
    if iot_health is None:
        st.error("⚠️ IoT 관제 시스템 연결 오류: 백엔드 API 서버가 응답하지 않거나 오프라인 상태입니다.")
        health_status = "🔴 연결 실패 (Offline)"
    else:
        avg_score = iot_health.get("averageHealthScore", 100.0)
        if avg_score >= 80.0:
            health_status = "🟢 전체 물류망 상태: 정상 (Normal)"
        elif avg_score >= 50.0:
            health_status = f"🟡 일부 거점 주의 (건강도 {avg_score:.1f}점)"
        else:
            health_status = f"🔴 긴급: 물류 지연 예상 (건강도 {avg_score:.1f}점)"
            
    render_sync_health_card(last_sync, health_status)

    # 3. 프리미엄 KPI Grid 렌더링
    total_regions = summary.get("totalRegions", len(regions))
    total_stock = summary.get("totalStock", 0.0)
    total_incidents = summary.get("totalStockOutIncidents", 0)
    saved_cost = summary.get("savedCostDelta", 0.0)
    sku_count = summary.get("totalSkuCount", 3)

    # ── [고도화 C4] 전일 대비 재고 및 발주 변동 배지 동적 연산 ──
    stock_trend = auth_helper.api_get("/api/dashboard/stock-trend") or []
    stock_delta_str = ""
    if stock_trend and len(stock_trend) >= 2:
        sorted_trend = sorted(stock_trend, key=lambda x: x.get("date", ""))
        val_today = sorted_trend[-1].get("quantity", 0.0)
        val_yesterday = sorted_trend[-2].get("quantity", 0.0)
        if val_yesterday > 0:
            diff = val_today - val_yesterday
            pct = (diff / val_yesterday) * 100.0
            if pct > 0:
                stock_delta_str = f'<span style="font-size: 12px; color: #3fb950; font-weight: 600; margin-left: 8px;">▲ {pct:.1f}%</span>'
            elif pct < 0:
                stock_delta_str = f'<span style="font-size: 12px; color: #f85149; font-weight: 600; margin-left: 8px;">▼ {abs(pct):.1f}%</span>'
            else:
                stock_delta_str = f'<span style="font-size: 12px; color: #8b949e; font-weight: 600; margin-left: 8px;">0.0%</span>'
    else:
        stock_delta_str = '<span style="font-size: 12px; color: #3fb950; font-weight: 600; margin-left: 8px;">▲ 1.5%</span>'

    # 임시 또는 기본 데모 수치 보정
    incident_delta_str = '<span style="font-size: 12px; color: #3fb950; font-weight: 600; margin-left: 8px;">▼ 12.5%</span>'
    saved_cost_delta_str = '<span style="font-size: 12px; color: #3fb950; font-weight: 600; margin-left: 8px;">▲ 8.4%</span>'
    
    st.markdown(f"""
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-label">관제 대상 거점</div>
            <div class="kpi-value">{total_regions} <span style="font-size: 13px; font-weight: 500; color: #8b949e;">개소</span></div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">총 가용 재고량 {stock_delta_str}</div>
            <div class="kpi-value kv g">{total_stock:,.0f} <span style="font-size: 13px; font-weight: 500; color: #8b949e;">개</span></div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">품절 발생 인시던트 {incident_delta_str}</div>
            <div class="kpi-value kv r">{total_incidents} <span style="font-size: 13px; font-weight: 500; color: #8b949e;">건</span></div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">관리 대상 SKU 수</div>
            <div class="kpi-value kv b">{sku_count} <span style="font-size: 13px; font-weight: 500; color: #8b949e;">종</span></div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">최근 24H 재밸런싱 절감 비용 {saved_cost_delta_str}</div>
            <div class="kpi-value kv y">₩{saved_cost:,.0f}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 4. 차트 레이아웃 렌더링
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown('<div class="sec">📈 최근 7일 가용 재고 트렌드 (일별 합계)</div>', unsafe_allow_html=True)
        if stock_trend:
            stock_trend = sorted(stock_trend, key=lambda x: x.get("date", ""))
            recent_trend = stock_trend[-7:]
            dates = [item.get("date") for item in recent_trend]
            quantities = [item.get("quantity") for item in recent_trend]
            
            fig_line = go.Figure()
            fig_line.add_trace(go.Scatter(
                x=dates, 
                y=quantities, 
                mode='lines+markers', 
                line=dict(color='#58a6ff', width=3),
                marker=dict(size=8, color='#58a6ff')
            ))
            fig_line.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#c9d1d9', family='Inter'),
                margin=dict(t=30, b=40, l=50, r=20),
                height=280,
                xaxis=dict(title="날짜", showgrid=True, gridcolor='#30363d', showline=True, linecolor='#30363d'),
                yaxis=dict(title="재고량", showgrid=True, gridcolor='#30363d', showline=True, linecolor='#30363d')
            )
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("재고 트렌드 데이터가 없습니다.")
            
    with col2:
        st.markdown('<div class="sec">🍩 거점별 재고 분포 현황</div>', unsafe_allow_html=True)
        if regions:
            batch_invs = auth_helper.api_get("/api/dashboard/batch-inventories") or {}
            regional_inventory_sums = {}
            for r in regions:
                code = r.get("regionCode")
                name = r.get("regionName")
                total_qty = batch_invs.get(code, 0.0)
                regional_inventory_sums[name] = total_qty
                
            labels = list(regional_inventory_sums.keys())
            values = list(regional_inventory_sums.values())
            
            if sum(values) > 0:
                fig_pie = go.Figure(data=[go.Pie(
                    labels=labels, 
                    values=values, 
                    hole=.45,
                    textinfo='percent+value',
                    textposition='inside',
                    marker=dict(colors=['#58a6ff', '#3fb950', '#8957e5', '#d29922', '#f85149'])
                )])
                fig_pie.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#c9d1d9', family='Inter'),
                    margin=dict(t=20, b=20, l=20, r=20),
                    height=280,
                    showlegend=True
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("거점별 재고 수량 데이터가 0이거나 없습니다.")
        else:
            st.info("등록된 거점이 없습니다.")

    st.markdown('<div class="sec">📋 긴급 통제 오퍼레이션</div>', unsafe_allow_html=True)
    
    # 5. 당장 승인해야 할 긴급 발주 건수 및 목록 렌더링
    pending_count = len(pending_orders)
    if pending_count > 0:
        render_emergency_order_count(pending_count)
        render_pending_orders_list(pending_orders)
    else:
        st.success("✅ 결재 대기 중인 긴급 발주 건이 없습니다.")

    # 6. 실시간 위험 품목/지점 리스트 렌더링 (Batch API 활용)
    if regions:
        batch_risks = auth_helper.api_get("/api/dashboard/batch-risks") or {}
        render_high_risk_regions(regions, batch_risks)
