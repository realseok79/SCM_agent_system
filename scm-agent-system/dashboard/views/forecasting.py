# dashboard/views/forecasting.py
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
    # CSS 스타일 주입
    inject_custom_css()


    st.markdown(f'<div class="hdr"><div><div class="hdr-t">📈 수요 예측 및 출고 분석 관제탑</div><div class="hdr-s">과거 이력과 확률 모델을 기반으로 최적 안전재고 및 미래 수요 예측 분석을 수행합니다.</div></div></div>', unsafe_allow_html=True)
    
    regions = auth_helper.api_get("/api/regions")
    if not regions:
        st.warning("⚠️ 지점 정보가 로드되지 않았습니다. 지역별 관제 센터에서 지점을 먼저 확인해 주세요.")
        return
        
    conn = auth_helper.get_local_connection()
    cursor = conn.cursor()
    
    col1, col2 = st.columns([1, 2.2])
    
    abc_classes = {}
    with col1:
        st.markdown('<div class="sec">대상 지점 및 품목 필터</div>', unsafe_allow_html=True)
        region_options = {f"{r['regionName']} ({r['regionCode']})": r for r in regions}
        selected_region_key = st.selectbox("조회 대상 지점 선택", options=list(region_options.keys()), key="df_selected_region")
        selected_region = region_options[selected_region_key]
        region_code = selected_region["regionCode"]
        
        products = ["마스크", "반도체 칩", "종합 품목"]
        selected_product = st.selectbox("조회 대상 품목 선택", options=products, key="df_selected_product")
        
        st.markdown('<div class="sec">30일 누적 ABC 등급 분석</div>', unsafe_allow_html=True)
        
        cursor.execute("""
            SELECT product_name, SUM(outbound_qty) as total_qty
            FROM stock_out_logs
            WHERE timestamp >= datetime('now', '-30 days')
            GROUP BY product_name
            ORDER BY total_qty DESC
        """)
        abc_rows = cursor.fetchall()
        
        if abc_rows:
            abc_data = [{"product": r[0], "qty": r[1]} for r in abc_rows]
            total_abc_qty = sum(item["qty"] for item in abc_data)
            
            cumulative = 0
            for item in abc_data:
                cumulative += item["qty"]
                pct = (cumulative / total_abc_qty) * 100 if total_abc_qty > 0 else 0
                if pct <= 70:
                    abc_classes[item["product"]] = "A (핵심 품목)"
                elif pct <= 90:
                    abc_classes[item["product"]] = "B (일반 품목)"
                else:
                    abc_classes[item["product"]] = "C (악성/잔여 품목)"
            
            current_class = abc_classes.get(selected_product, "C (악성/잔여 품목)")
            color_class = "g" if "A" in current_class else ("y" if "B" in current_class else "r")
            
            st.markdown(f"""
            <div class="kc" style="margin-bottom: 8px;">
                <div class="kl">선택 품목 ABC 등급</div>
                <div class="kv {color_class}">{current_class}</div>
                <div class="ku">최근 30일 누적 출고량 비중 기준 등급 분류</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("💡 과거 90일 데이터가 아직 생성되지 않았습니다.")
            
    with col2:
        st.markdown(f'<div class="sec">📈 최근 30일간 일별 출고량 추이 및 7일 이동평균선 ([{selected_product}] - {selected_region["regionName"]})</div>', unsafe_allow_html=True)
        
        cursor.execute("""
            SELECT date, daily_outbound_total, moving_avg_30d
            FROM daily_demand_stats
            WHERE region_code = ? AND product_name = ?
            ORDER BY date DESC LIMIT 30
        """, (region_code, selected_product))
        stats_rows = cursor.fetchall()
        
        if stats_rows:
            stats_rows.reverse()
            df_stats = pd.DataFrame([
                {
                    "date": r["date"], 
                    "outbound": r["daily_outbound_total"], 
                    "moving_avg": r["moving_avg_30d"]
                } for r in stats_rows
            ])
            
            fig, ax = plt.subplots(figsize=(10, 2.5), dpi=100)
            fig.patch.set_facecolor(BG)
            ax.set_facecolor(BG)
            
            ax.bar(df_stats["date"], df_stats["outbound"], color="#8ab4f8", alpha=0.3, label="일일 출고량")
            ax.plot(df_stats["date"], df_stats["moving_avg"], color="#00e5a0", lw=1.8, label="7일 이동평균선")
            
            sax(ax)
            ax.set_xlabel("일자 (Date)", fontsize=8, color=TX)
            ax.set_ylabel("수량 (Units)", fontsize=8, color=TX)
            ax.legend(fontsize=7, framealpha=0, loc="upper left", labelcolor=TX)
            fig.tight_layout(pad=0.5)
            st.pyplot(fig, use_container_width=True)
        else:
            st.info("💡 출고 집계 데이터가 부족합니다.")
 
    st.markdown('<div class="sec">📊 전체 품목 ABC 분석 파레토(Pareto) 차트 & 미래 수요 예측 통계</div>', unsafe_allow_html=True)
    col3, col4 = st.columns([1.5, 1.7])
    
    with col3:
        st.markdown('<div class="cc"><div class="ct"><span class="dt" style="background:#fdd663"></span>최근 30일 누적 파레토 등급선</div>', unsafe_allow_html=True)
        
        if abc_rows:
            df_abc = pd.DataFrame([{"product_name": r[0], "total_qty": r[1]} for r in abc_rows])
            total_abc = df_abc["total_qty"].sum()
            df_abc["cum_qty"] = df_abc["total_qty"].cumsum()
            df_abc["cum_pct"] = (df_abc["cum_qty"] / total_abc) * 100 if total_abc > 0 else 0.0
            
            fig, ax1 = plt.subplots(figsize=(8, 3.2), dpi=100)
            fig.patch.set_facecolor(BG)
            ax1.set_facecolor(BG)
            
            colors = ["#00e5a0" if idx == 0 else ("#fdd663" if idx == 1 else "#ff5c5c") for idx in range(len(df_abc))]
            bars = ax1.bar(df_abc["product_name"], df_abc["total_qty"], color=colors, alpha=0.6, width=0.4, label="출고량")
            ax1.set_ylabel("누적 출고량 (Units)", color=TX, fontsize=8)
            ax1.tick_params(colors=TX, labelsize=7)
            
            ax2 = ax1.twinx()
            ax2.plot(df_abc["product_name"], df_abc["cum_pct"], color="#8ab4f8", marker="D", ms=4, lw=1.6, label="누적 비중 (%)")
            ax2.set_ylabel("누적 비중 (%)", color=TX, fontsize=8)
            ax2.tick_params(colors=TX, labelsize=7)
            ax2.set_ylim(0, 110)
            
            ax2.axhline(80.0, color="#ff5c5c", linestyle="--", lw=1.0, alpha=0.7)
            
            for ax in [ax1, ax2]:
                ax.spines["top"].set_visible(False)
                for spine in ax.spines.values():
                    spine.set_color('#3c4043')
            
            fig.tight_layout()
            st.pyplot(fig, use_container_width=True)
        else:
            st.info("💡 파레토 데이터 부족")
        st.markdown('</div>', unsafe_allow_html=True)
            
    with col4:
        st.markdown('<div class="cc"><div class="ct"><span class="dt" style="background:#00e5a0"></span>지능형 적정 안전재고 및 ROP 추천 마스터 테이블</div>', unsafe_allow_html=True)
        
        from agents.analysis_agent import AnalysisAgent
        from dto.schemas import DataDTO
        
        analysis_agent = AnalysisAgent()
        table_records = []
        for prod in ["마스크", "반도체 칩", "종합 품목"]:
            cursor.execute("""
                SELECT quantity FROM region_inventory
                WHERE region_code = ? AND product_name = ?
                ORDER BY date DESC LIMIT 1
            """, (region_code, prod))
            s_row = cursor.fetchone()
            current_qty = s_row[0] if s_row else 1500.0
            
            cursor.execute("""
                SELECT outbound_qty FROM stock_out_logs
                WHERE region_code = ? AND product_name = ?
                ORDER BY timestamp DESC LIMIT 30
            """, (region_code, prod))
            hist_rows = cursor.fetchall()
            history_d = [float(r[0]) for r in hist_rows] if hist_rows else [100.0] * 10
            
            avg_daily_demand = sum(history_d) / len(history_d) if history_d else 100.0
            cost_h = 2.0 if prod == "마스크" else (15.0 if prod == "반도체 칩" else 5.0)
            stockout_p = 15.0 if prod == "마스크" else (80.0 if prod == "반도체 칩" else 30.0)
            
            data_dto = DataDTO(
                timestamp=datetime.now().isoformat(),
                day=90,
                daily_demand=history_d[0] if history_d else 100.0,
                current_stock=current_qty,
                lead_time_days=7.0,
                weather_index=1.0,
                macro_trend=1.0,
                history_demand=history_d,
                history_lead_time=[7.0] * len(history_d),
                unit_holding_cost=cost_h,
                stockout_penalty=stockout_p,
                order_fixed_cost=200.0
            )
            
            signal_dto = analysis_agent.analyze(data_dto)
            forecast_7d = avg_daily_demand * 7
            forecast_14d = avg_daily_demand * 14
            prod_class = abc_classes.get(prod, "C (악성)")
            
            table_records.append({
                "품목명": prod,
                "등급 (ABC)": prod_class,
                "현재 재고": f"{current_qty:,.0f} 개",
                "7일 예측수요": f"{forecast_7d:,.0f} 개",
                "14일 예측수요": f"{forecast_14d:,.0f} 개",
                "안전 재고": f"{signal_dto.safety_stock:,.0f} 개",
                "발주점 (ROP)": f"{signal_dto.reorder_point:,.0f} 개",
                "최적 발주량": f"{signal_dto.optimal_order_qty:,.0f} 개"
            })
            
        html_table = """
        <div class="gt">
            <table>
                <thead>
                    <tr>
                        <th>품목명</th>
                        <th>등급</th>
                        <th>현재 재고</th>
                        <th>7일 수요예측</th>
                        <th>14일 수요예측</th>
                        <th>안전재고(SS)</th>
                        <th>발주점(ROP)</th>
                        <th>추천 발주량</th>
                    </tr>
                </thead>
                <tbody>
        """
        for r in table_records:
            cls_color = "#00e5a0" if "A" in r["등급 (ABC)"] else ("#fdd663" if "B" in r["등급 (ABC)"] else "#ff5c5c")
            html_table += f"""
                    <tr>
                        <td style="font-weight:bold; color:#8ab4f8;">{r['품목명']}</td>
                        <td style="color:{cls_color}; font-weight:bold;">{r['등급 (ABC)']}</td>
                        <td>{r['현재 재고']}</td>
                        <td>{r['7일 예측수요']}</td>
                        <td>{r['14일 예측수요']}</td>
                        <td style="color:#00e5a0;">{r['안전 재고']}</td>
                        <td style="color:#fdd663; font-weight:bold;">{r['발주점 (ROP)']}</td>
                        <td style="color:#8ab4f8; font-weight:bold;">{r['최적 발주량']}</td>
                    </tr>
            """
        html_table += """
                </tbody>
            </table>
        </div>
        """
        st.markdown(html_table, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
    conn.close()

if __name__ == "__main__":
    show()
