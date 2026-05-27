# dashboard/views/regional/chart_tab.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import auth_helper
from components.styles import TX

def render_regional_charts(selected_region):
    st.markdown('<div class="sec">실시간 지역 재고 흐름 & 기상 융합 분석</div>', unsafe_allow_html=True)
    
    if not selected_region:
        st.info("데이터를 업로드하면 지역이 자동 등록되고 상세 대시보드가 활성화됩니다.")
        return

    # 1. 해당 지역 재고 데이터 조회
    inv_data = auth_helper.api_get(f"/api/dashboard/region/{selected_region['regionCode']}/inventory")
    if not inv_data:
        st.info("분석을 진행하기 위해 좌측 패널에서 재고 데이터를 업로드해 주세요.")
        return

    inv_df = pd.DataFrame([
        {
            "product_name": inv["id"]["productName"],
            "date": inv["id"]["date"],
            "quantity": inv["quantity"]
        } for inv in inv_data
    ])

    # 2. 기상 데이터 조회
    weather_data = auth_helper.api_get(f"/api/dashboard/region/{selected_region['regionCode']}/weather")
    weather_df = pd.DataFrame(weather_data) if weather_data else pd.DataFrame()

    # 재고 KPI 카드 렌더링
    inv_df["quantity"] = pd.to_numeric(inv_df["quantity"], errors="coerce").fillna(0)
    
    active_products = []
    for p in inv_df["product_name"].unique():
        p_df = inv_df[inv_df["product_name"] == p].sort_values("date")
        if not p_df.empty and p_df["quantity"].iloc[-1] > 0:
            active_products.append(p)
            
    products = active_products
    
    if not products:
        st.info("분석할 만한 유효 재고(최신 물량 > 0)를 가진 품목이 없습니다.")
        return

    total_qty = inv_df[inv_df["product_name"].isin(products)].groupby("product_name")["quantity"].last().sum()

    st.markdown(f'''<div class="kg">
    <div class="kc"><div class="kl">모니터링 품목수</div><div class="kv">{len(products)} SKU</div><div class="ku">지정 품목 리스트</div></div>
    <div class="kc"><div class="kl">최신 총 재고량</div><div class="kv b">{total_qty:,.0f}</div><div class="ku">units (마지막 일자 기준)</div></div>
    <div class="kc"><div class="kl">기상 관측일수</div><div class="kv g">{len(weather_df)}일</div><div class="ku">동기화 완료</div></div>
    </div>''', unsafe_allow_html=True)

    # 품목 선택 필터
    selected_prod = st.selectbox("분석할 품목 선택", options=products)
    st.session_state["active_product_name"] = selected_prod
    prod_inv = inv_df[inv_df["product_name"] == selected_prod]

    # 1. 재고 변동 차트 시각화 및 2. 데이터 무결성 검증
    if prod_inv.empty or prod_inv["quantity"].iloc[-1] <= 0:
        st.info(f"[{selected_prod}] 품목은 현재 재고가 없어 차트 및 무결성 분석을 제공하지 않습니다.")
    else:
        st.markdown(f'<div class="cc"><div class="ct"><span class="dt" style="background:#8ab4f8"></span>[{selected_prod}] 일별 재고 변동 추이</div>', unsafe_allow_html=True)
        
        dates_parsed = pd.to_datetime(prod_inv["date"])
        prod_inv = prod_inv.assign(parsed_date=dates_parsed)
        prod_inv = prod_inv.sort_values("parsed_date")
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=prod_inv["date"],
            y=prod_inv["quantity"],
            mode="lines+markers+text",
            name="재고량",
            line=dict(color="#8ab4f8", width=2.5),
            marker=dict(color="#c9d1d9", size=6, line=dict(color="#8ab4f8", width=1.5)),
            text=[f"{int(y):,}" for y in prod_inv["quantity"]],
            textposition="top center",
            textfont=dict(color=TX, size=9),
            fill="tozeroy",
            fillcolor="rgba(138, 180, 248, 0.06)",
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
                title=dict(text="날짜 (Date)", font=dict(color=TX, size=10))
            ),
            yaxis=dict(
                gridcolor="rgba(255, 255, 255, 0.06)",
                linecolor="rgba(255, 255, 255, 0.12)",
                tickfont=dict(color=TX, size=9),
                title=dict(text="수량 (Units)", font=dict(color=TX, size=10))
            )
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # 직관적인 재고 이력 표 추가
        st.write("선택 품목 일별 재고 원시 데이터")
        raw_table_df = prod_inv[["date", "quantity"]].copy()
        raw_table_df.columns = ["날짜", "재고 수량 (Units)"]
        st.dataframe(raw_table_df.set_index("날짜"), use_container_width=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

        # 2. 데이터 무결성 검증
        st.markdown('<div class="sec">재고 효율성 및 데이터 무결성 관제탑</div>', unsafe_allow_html=True)
        latest_date = prod_inv["date"].iloc[-1]
        
        integrity_result = auth_helper.api_get(f"/api/dashboard/region/{selected_region['regionCode']}/integrity?product={selected_prod}&date={latest_date}")
        if integrity_result:
            if integrity_result.get("isConsistent", True):
                st.success(f" 데이터 무결성 검증 완료 | {integrity_result.get('message')}")
            else:
                st.error(f" 무결성 불일치 발생 | {integrity_result.get('message')}")
