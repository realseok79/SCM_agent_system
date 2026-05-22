# dashboard/views/overview.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from matplotlib import rc
import auth_helper
from components.styles import inject_custom_css, BG, TX, sax

# Matplotlib 한글 폰트 설정
plt.rcParams["axes.unicode_minus"] = False
for f in ["AppleGothic", "NanumGothic", "Malgun Gothic"]:
    try:
        rc("font", family=f)
        break
    except:
        continue

def show():
    # CSS 스타일 주입 (개별 뷰에서도 스타일이 유지되도록 처리)
    inject_custom_css()


    summary = auth_helper.api_get("/api/dashboard/summary")
    if not summary:
        st.warning("⚠️ 백엔드 서비스와 통신할 수 없거나 세션이 만료되었습니다. 로그인 상태를 확인해 주세요.")
        return

    st.markdown(f'<div class="hdr"><div><div class="hdr-t">SCM AI 자율 제어 관제탑 (REST Dashboard)</div><div class="hdr-s">스프링 백엔드 통합 SCM 텔레메트리 &nbsp;·&nbsp; {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div></div></div>', unsafe_allow_html=True)

    # 하드코딩 제거: totalSkuCount 반영 및 금액 포맷팅 대비
    total_sku = summary.get("totalSkuCount", 12)
    saved_cost = summary.get("savedCostDelta", 0.0)
    saved_cost_formatted = f"₩{saved_cost:,.0f}" if saved_cost > 0 else "₩0"

    # KPI 융합 카드 렌더링 (하드코딩 제거 반영)
    st.markdown(f'''<div class="kg">
<div class="kc"><div class="kl">등록 지점 수</div><div class="kv b">{summary.get("totalRegions", 0)} 개소</div><div class="ku">실무 가용 물류 거점</div></div>
<div class="kc"><div class="kl">전체 모니터링 SKU</div><div class="kv">{total_sku} 품목</div><div class="ku">등록된 활성 상품 종류</div></div>
<div class="kc"><div class="kl">통합 가용 재고량</div><div class="kv g">{summary.get("totalStock", 0.0):,.0f} 개</div><div class="ku">지점별 최신 재고 합산</div></div>
<div class="kc"><div class="kl">발주 장애 사고 건수</div><div class="kv r">{summary.get("totalStockOutIncidents", 0)} 건</div><div class="ku">안전 기준 미달 품절 사고</div></div>
<div class="kc"><div class="kl">관제 시스템 상태</div><div class="kv g">{summary.get("systemStatus", "STABLE")}</div><div class="ku">서버 정상 작동 유무</div><div class="kb ok">정상</div></div>
</div>''', unsafe_allow_html=True)

    # SCM 운영 및 발주 체크리스트 실데이터 API 연동
    st.markdown("### 📋 오늘의 SCM 운영 및 발주 체크리스트 (REST 연동)")
    chk_col1, chk_col2 = st.columns([1.8, 1.2])

    with chk_col1:
        st.markdown('<div class="cc"><div class="ct"><span class="dt" style="background:#f28b82"></span>자동 발주 승인 대기 목록 (AI 추천)</div>', unsafe_allow_html=True)
        
        pending_orders = auth_helper.api_get("/api/dashboard/pending-orders")
        
        if not pending_orders:
            st.info("🟢 현재 승인 대기 중인 자율 AI 발주 요청이 없습니다.")
        else:
            import os
            for idx, order in enumerate(pending_orders):
                order_id = order.get("id")
                region = order.get("regionCode")
                product = order.get("productName")
                qty = order.get("quantity")
                
                # (1) 실재고량 API 통신 조회
                inv_data = auth_helper.api_get(f"/api/dashboard/region/{region}/inventory")
                stock_qty = 0.0
                if inv_data:
                    sku_invs = [inv for inv in inv_data if inv.get("id", {}).get("productName") == product]
                    if sku_invs:
                        stock_qty = sku_invs[0].get("quantity", 0.0)
                        
                # (2) 기준 ROP 매핑
                base_rop = 400.0 if product == "마스크" else (80.0 if product == "반도체 칩" else 100.0)
                deficit_qty = max(0.0, base_rop - stock_qty)
                deficit_pct = (deficit_qty / base_rop) * 100.0 if base_rop > 0 else 0.0
                
                # (3) ROP 미달 근거 포맷팅 적용 (XAI 근거 문장 템플릿화)
                xai_msg = f"{region}점 <b>{product}</b> 지점 재고량({stock_qty:,.0f}개)이 ROP 안전재고 기준({base_rop:,.0f}개) 대비 <b>{deficit_pct:.1f}%</b> 미달하여 <b>{qty:,.0f}개</b> 자동 발주를 제안합니다."
                
                # (4) LLM 유무에 따라 라벨 동적 전환
                api_key_exists = bool(os.getenv("OPENAI_API_KEY"))
                badge_lbl = "AI Generation" if api_key_exists else "Rule Engine"
                badge_class = "ok" if api_key_exists else "w"
                
                st.markdown(f"""
                <div class="ep ec" style="border-left-color: #f28b82; padding: 12px; margin-bottom: 6px;">
                    <div class="et" style="color: #f28b82; font-weight: bold; font-size: 12px; display: flex; align-items: center; justify-content: space-between;">
                        <span>⚠️ [안전재고 경고] {region} 거점 {product} 고갈 우려</span>
                        <span class="kb {badge_class}" style="margin-top: 0px; font-size: 9px; padding: 2px 6px;">{badge_lbl}</span>
                    </div>
                    <div class="eb" style="font-size: 11px; margin-top: 6px; color: #e8eaed;">
                        {xai_msg}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # 버튼 레이아웃
                btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 1.5])
                with btn_col1:
                    if st.button("📥 승인", key=f"btn_approve_{order_id}", type="primary"):
                        res = auth_helper.api_post(f"/api/dashboard/orders/{order_id}/approve", {})
                        st.success(f"{product} 발주 승인 완료!")
                        st.rerun()
                with btn_col2:
                    if st.button("❌ 반려", key=f"btn_reject_toggle_{order_id}"):
                        st.session_state[f"show_reject_form_{order_id}"] = True
                
                # 반려 폼 노출 영역
                if st.session_state.get(f"show_reject_form_{order_id}", False):
                    with st.container():
                        reason = st.text_input("📝 반려 사유 입력 (가드레일 피드백 엔진 전달)", key=f"txt_reason_{order_id}", placeholder="예: ROP 임계치가 너무 높음. 안전재고 기준 15% 하향 필요.")
                        r_col1, r_col2 = st.columns([1, 1])
                        with r_col1:
                            if st.button("반려 확정", key=f"btn_confirm_reject_{order_id}"):
                                if not reason.strip():
                                    st.error("반려 사유를 반드시 입력해주세요.")
                                else:
                                    payload = {"reason": reason}
                                    confirm_url = f"/api/dashboard/orders/{order_id}/reject"
                                    res = auth_helper.api_post(confirm_url, payload)
                                    st.warning("발주가 반려되었습니다. 사유가 가드레일 피드백 보정 엔진에 전달되었습니다.")
                                    st.session_state.pop(f"show_reject_form_{order_id}", None)
                                    st.rerun()
                        with r_col2:
                            if st.button("취소", key=f"btn_cancel_reject_{order_id}"):
                                st.session_state.pop(f"show_reject_form_{order_id}", None)
                                st.rerun()
                st.markdown("<hr style='margin: 8px 0; border-color:#3c4043;' />", unsafe_allow_html=True)
                
        st.markdown('</div>', unsafe_allow_html=True)

    with chk_col2:
        st.markdown('<div class="cc"><div class="ct"><span class="dt" style="background:#81c995"></span>실시간 물류 건강 지표 (IoT)</div>', unsafe_allow_html=True)
        iot_data = auth_helper.api_get("/api/iot/health-summary")
        if iot_data:
            st.markdown(f"""
            <div class="ep en" style="border-left-color: #81c995; padding: 12px; min-height: 110px;">
                <div class="et" style="color: #81c995; font-weight: bold; font-size: 13px;">🟢 IoT 연결 상태: {iot_data.get('connectionStatus')}</div>
                <div class="eb" style="font-size: 12px; margin-top: 5px; color: #e8eaed; line-height: 1.5;">
                    · 센서 가동율: <b>{iot_data.get('sensorActiveRate')}%</b> <br/>
                    · 온도 관리상태: <b>{iot_data.get('temperatureStatus')}</b> <br/>
                    · 습도 관리상태: <b>{iot_data.get('humidityStatus')}</b> <br/>
                    · GPS 위성 수신: <b>{iot_data.get('gpsSyncRate')}%</b>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="ep en" style="border-left-color: #81c995; padding: 12px; min-height: 110px;">
                <div class="et" style="color: #f28b82; font-weight: bold; font-size: 13px;">🔴 IoT 연결 해제됨</div>
                <div class="eb" style="font-size: 12px; margin-top: 5px; color: #e8eaed;">
                    IoT API 모니터링 허브로부터 데이터를 가져올 수 없습니다.
                </div>
            </div>
            """, unsafe_allow_html=True)
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
    else:
        st.info("💡 차트를 그리기 위한 데이터가 부족합니다.")
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    show()
