# dashboard/views/comparison.py
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import auth_helper
from agents.baseline_agent import BaselineAgent
from components.styles import inject_custom_css, BG, TX, sax


@st.cache_data
def get_cached_simulation(sku, unit_price, holding_cost, base_demand, lead_time, initial_stock, days, alpha_factor):
    agent = BaselineAgent()
    return agent.run_simulation(
        sku=sku,
        unit_price=unit_price,
        holding_cost=holding_cost,
        base_demand=base_demand,
        lead_time=lead_time,
        initial_stock=initial_stock,
        days=days,
        alpha_factor=alpha_factor
    )

def show():
    # CSS 스타일 주입 (수려한 어두운 모드 UX)
    inject_custom_css()

    st.markdown('<div class="hdr"><div><div class="hdr-t">100일 SCM 자본 효율성 시뮬레이션 비교 (대조군 vs 실험군)</div><div class="hdr-s">30일 이동평균 대조군 &nbsp;·&nbsp; 포아송 확률론적 AI 가드레일 실험군의 비용구조 정량 비교</div></div></div>', unsafe_allow_html=True)

    # 1. API를 통한 금융 마스터 테이블 정보 수집
    financials = auth_helper.api_get("/api/dashboard/financials")
    if not financials:
        st.warning("⚠️ 금융 마스터 정보를 수집하지 못했습니다.")
        return

    # 사이드바 혹은 좌측 컬럼 제어 패널 구성
    col_panel, col_chart = st.columns([1.1, 2.3])

    with col_panel:
        st.markdown('<div class="sec">시뮬레이션 변수 조절</div>', unsafe_allow_html=True)
        
        sku_options = {f"{f['productName']} (단가: {f['unitPrice']:,}원)": f for f in financials}
        selected_sku_key = st.selectbox("분석 대상 SKU 선택", options=list(sku_options.keys()))
        selected_sku = sku_options[selected_sku_key]

        # 슬라이더 파라미터 조절 (st.cache_data가 이 파라미터 변화에만 동적 반응함)
        base_demand = st.slider("일평균 수요량 (Poisson λ)", min_value=10.0, max_value=200.0, value=40.0, step=5.0)
        lead_time = st.slider("표준 리드타임 (Days)", min_value=1, max_value=10, value=3)
        initial_stock = st.slider("초기 재고량 (Units)", min_value=50, max_value=1500, value=300, step=50)
        
        # 가드레일 피드백 보정 계수
        alpha_factor = st.slider("가드레일 ROP 보정 계수 (α)", min_value=0.5, max_value=1.5, value=1.0, step=0.05,
                                 help="Day 4 피드백 엔진에 의해 캘리브레이션되는 ROP 임계점 보정 변수입니다.")

        days_param = 100

        # 품목 금융 마스터 정보 대입
        unit_price = selected_sku["unitPrice"]
        holding_cost = selected_sku["holdingCostPerDay"]

        st.markdown(f"""
        <div class="kc" style="margin-top: 10px;">
            <div class="kl">품목 재무 표준</div>
            <div class="kv b" style="font-size: 16px;">개당 일 보관비: {holding_cost:.2f}원</div>
            <div class="ku">주문비(10%): {unit_price * 0.1:,.0f}원 / 건<br/>품절 페널티(150%): {unit_price * 1.5:,.0f}원 / 개</div>
        </div>
        """, unsafe_allow_html=True)

    # 2. 캐시 기반 시뮬레이션 연산
    sim_res = get_cached_simulation(
        sku=selected_sku["productName"],
        unit_price=unit_price,
        holding_cost=holding_cost,
        base_demand=base_demand,
        lead_time=lead_time,
        initial_stock=initial_stock,
        days=days_param,
        alpha_factor=alpha_factor
    )

    c_data = sim_res["control"]
    t_data = sim_res["test"]

    # ROI 계산 및 절감율
    cost_diff = c_data["total_cost"] - t_data["total_cost"]
    saving_rate = (cost_diff / c_data["total_cost"]) * 100.0 if c_data["total_cost"] > 0 else 0.0

    with col_chart:
        # 상단 핵심 ROI 비교 카드
        st.markdown('<div class="sec">정량적 비용 절감 성과 (ROI)</div>', unsafe_allow_html=True)
        
        saving_color = "g" if cost_diff > 0 else "r"
        st.markdown(f'''<div class="kg">
        <div class="kc"><div class="kl">대조군 총비용 (이동평균)</div><div class="kv">{c_data["total_cost"]:,.0f}원</div><div class="ku">평균 재고: {c_data["avg_stock"]:.1f}개</div></div>
        <div class="kc"><div class="kl">실험군 총비용 (확률론적 AI)</div><div class="kv b">{t_data["total_cost"]:,.0f}원</div><div class="ku">평균 재고: {t_data["avg_stock"]:.1f}개</div></div>
        <div class="kc"><div class="kl">누적 자본 절감액</div><div class="kv {saving_color}">{abs(cost_diff):,.0f}원 {"절감" if cost_diff > 0 else "손실"}</div><div class="ku">100일 누계 기준</div></div>
        <div class="kc"><div class="kl">자본 효율 개선율</div><div class="kv g">{saving_rate:.1f}%</div><div class="ku">총비용 대비 절감비율</div></div>
        </div>''', unsafe_allow_html=True)

        # 항목별 비용 분해 막대 그래프 렌더링
        st.markdown('<div class="sec">비용 항목별 분해 비교 (물류비 vs 보관비 vs 기회비)</div>', unsafe_allow_html=True)
        
        fig, ax = plt.subplots(figsize=(10, 2.4), dpi=100)
        fig.patch.set_facecolor(BG)
        ax.set_facecolor(BG)

        labels = ['보관 비용\n(Holding)', '주문 비용\n(Ordering)', '품절 패널티\n(Shortage)']
        c_costs = [c_data["holding_cost"], c_data["ordering_cost"], c_data["shortage_cost"]]
        t_costs = [t_data["holding_cost"], t_data["ordering_cost"], t_data["shortage_cost"]]

        x = np.arange(len(labels))
        width = 0.35

        ax.bar(x - width/2, c_costs, width, label='대조군 (정적 이동평균)', color='#ff5c5c', alpha=0.85)
        ax.bar(x + width/2, t_costs, width, label='실험군 (확률론적 AI)', color='#8ab4f8', alpha=0.85)

        ax.set_ylabel('누적 비용 (원)', fontsize=8, color=TX)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, color=TX)
        ax.legend(facecolor=BG, edgecolor='#3c4043', labelcolor=TX, fontsize=7)
        sax(ax)
        fig.tight_layout(pad=0.5)
        st.pyplot(fig, use_container_width=True)

        # 일별 재고 흐름 및 품절 발생 타임라인 차트
        st.markdown('<div class="sec">100일 일일 재고 변동 및 품절 추이 타임라인</div>', unsafe_allow_html=True)
        
        df_c = pd.DataFrame(c_data["history"])
        df_t = pd.DataFrame(t_data["history"])

        fig2, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 3.8), dpi=100, sharex=True)
        fig2.patch.set_facecolor(BG)
        ax1.set_facecolor(BG)
        ax2.set_facecolor(BG)

        # 재고 곡선
        ax1.plot(df_c["day"], df_c["stock"], label="대조군 재고", color="#ff5c5c", lw=1.2, ls="--")
        ax1.plot(df_t["day"], df_t["stock"], label="실험군 재고 (AI)", color="#8ab4f8", lw=1.5)
        ax1.set_ylabel("재고 수준 (Units)", fontsize=8, color=TX)
        ax1.legend(facecolor=BG, edgecolor='#3c4043', labelcolor=TX, fontsize=7, loc="upper right")
        sax(ax1)

        # 품절 기회 손실 막대
        ax2.bar(df_c["day"] - 0.2, df_c["shortage"], width=0.4, label="대조군 품절", color="#ff5c5c", alpha=0.5)
        ax2.bar(df_t["day"] + 0.2, df_t["shortage"], width=0.4, label="실험군 품절", color="#00e5a0", alpha=0.8)
        ax2.set_ylabel("일일 품절량 (Units)", fontsize=8, color=TX)
        ax2.set_xlabel("시뮬레이션 일자 (Days)", fontsize=8, color=TX)
        ax2.legend(facecolor=BG, edgecolor='#3c4043', labelcolor=TX, fontsize=7, loc="upper right")
        sax(ax2)

        fig2.tight_layout(pad=0.5)
        st.pyplot(fig2, use_container_width=True)

if __name__ == "__main__":
    show()
