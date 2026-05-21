# dashboard/views/regional.py
import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
from matplotlib import rc
import auth_helper

# Matplotlib 한글 폰트 설정
plt.rcParams["axes.unicode_minus"] = False
for f in ["AppleGothic", "NanumGothic", "Malgun Gothic"]:
    try:
        rc("font", family=f)
        break
    except:
        continue

BG = '#202124'
TX = '#e8eaed'

def sax(ax):
    ax.tick_params(colors=TX, labelsize=7)
    for spine in ax.spines.values():
        spine.set_color('#3c4043')
    ax.yaxis.grid(True, color="#3c4043", alpha=0.5, ls=":")
    ax.xaxis.grid(False)

def show():
    # CSS 스타일 주입 (다크 모드 글래스모피즘 효과 추가)
    st.markdown("""
    <style>
    .stApp{background:#202124;color:#e8eaed}
    .block-container, 
    [data-testid="stMainBlockContainer"], 
    [data-testid="stAppViewBlockContainer"] {
        padding: 0 1.5rem 0 1.5rem !important;
        max-width: 98% !important;
        width: 98% !important;
    }
    .hdr{background:#292a2d;border-bottom:1px solid #3c4043;padding:16px 16px 10px 16px;margin:0 -1.5rem 0.6rem !important;}
    .hdr-t{font-size:16px;font-weight:600;color:#e8eaed}
    .hdr-s{font-size:11px;color:#9aa0a6;margin-top:2px}
    .sec{font-size:11px;font-weight:600;color:#9aa0a6;text-transform:uppercase;letter-spacing:.06em;border-bottom:1px solid #3c4043;padding-bottom:4px;margin:0.8rem 0 0.4rem}
    .kg{display:grid;grid-template-columns:repeat(5,1fr);gap:6px;margin-bottom:0.3rem}
    .kc{background:#292a2d;border:1px solid #3c4043;border-radius:6px;padding:8px 12px}
    .kc:hover{border-color:#8ab4f8}
    .kl{font-size:9px;color:#9aa0a6;text-transform:uppercase;letter-spacing:.04em;margin-bottom:3px}
    .kv{font-size:22px;font-weight:400;color:#e8eaed;line-height:1.1}
    .kv.b{color:#8ab4f8}.kv.g{color:#81c995}.kv.y{color:#fdd663}.kv.r{color:#f28b82}
    .ku{font-size:9px;color:#5f6368;margin-top:2px}
    .kb{display:inline-block;font-size:8px;border-radius:3px;padding:1px 5px;margin-top:3px;border:1px solid}
    .kb.ok{background:#81c99511;color:#81c995;border-color:#81c99533}
    .kb.w{background:#f28b8211;color:#f28b82;border-color:#f28b8233}
    .cc{background:#292a2d;border:1px solid #3c4043;border-radius:6px;padding:8px 10px 4px;margin-bottom:4px}
    .ct{font-size:11px;font-weight:500;color:#e8eaed;margin-bottom:4px;display:flex;align-items:center;gap:6px}
    .dt{width:6px;height:6px;border-radius:50%;display:inline-block}
    .gt{background:#292a2d;border:1px solid #3c4043;border-radius:6px;overflow:hidden;margin-bottom:4px;width:100%}
    .gt table{width:100%;border-collapse:collapse;font-size:11px}
    .gt th{background:#303134;color:#9aa0a6;font-weight:500;font-size:9px;text-transform:uppercase;letter-spacing:.04em;padding:5px 8px;text-align:left;border-bottom:1px solid #3c4043}
    .gt td{padding:4px 8px;border-bottom:1px solid #3c4043;color:#e8eaed}
    </style>
    """, unsafe_allow_html=True)

    st.markdown(f'<div class="hdr"><div><div class="hdr-t">지역별 SCM 관제 센터 (REST 연동)</div><div class="hdr-s">2-Phase Commit 트랜잭션 격리 &nbsp;·&nbsp; 의미론적 스키마 매핑 보정 관제탑</div></div></div>', unsafe_allow_html=True)

    # 지역 조회
    regions = auth_helper.api_get("/api/regions")
    if regions is None:
        st.warning("⚠️ 지역 정보를 읽어오지 못했습니다.")
        return

    col1, col2 = st.columns([1.1, 2.1])

    with col1:
        st.markdown('<div class="sec">지역 관리 & 데이터 수집</div>', unsafe_allow_html=True)
        
        # 신규 지역 등록
        with st.expander("➕ 신규 지역 등록", expanded=False):
            with st.form("new_region_form"):
                new_name = st.text_input("지역명 (예: 서울, 부산, 경기, 제주 등)")
                new_desc = st.text_input("설명 (예: 수도권 메인 기지)")
                submit_btn = st.form_submit_button("지역 등록")
                
                if submit_btn:
                    if not new_name.strip():
                        st.error("지역명을 입력해주세요.")
                    else:
                        payload = {
                            "regionName": new_name,
                            "regionCode": new_name,
                            "description": new_desc
                        }
                        res = auth_helper.api_post("/api/regions", payload)
                        if res:
                            st.success("지역이 성공적으로 등록되었습니다.")
                            st.rerun()
                        else:
                            st.error("지역 등록 실패")

        if not regions:
            st.warning("⚠️ 등록된 지역이 없습니다. 먼저 지역을 등록해 주세요.")
            return

        region_options = {f"{r['regionName']} ({r['regionCode']})": r for r in regions}
        selected_key = st.selectbox("관제할 지역 선택", options=list(region_options.keys()))
        selected_region = region_options[selected_key]

        st.markdown(f"""
        <div class="kc" style="margin-bottom: 10px;">
            <div class="kl">선택된 지역 코드</div>
            <div class="kv b">{selected_region['regionCode']}</div>
            <div class="ku">{selected_region['description'] or '설명 없음'}</div>
        </div>
        """, unsafe_allow_html=True)

        # 데이터 업로드 (Phase A)
        st.markdown('<div class="sec">SCM 엑셀/CSV 데이터 업로드</div>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader("지역 재고 및 수요 이력 업로드", type=["csv", "xlsx", "xls"], key="regional_uploader")
        
        if uploaded_file is not None:
            if st.button("🚀 1단계: 데이터 파싱 및 분석 실행", key="btn_regional_route"):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                data = {"company_id": "COMPANY_SIGMA"}
                headers = {"Authorization": f"Bearer {st.session_state['access_token']}"}
                try:
                    upload_url = f"{auth_helper.API_BASE_URL}/api/regions/upload"
                    if st.session_state.get("use_mock_fallback"):
                        upload_url = "http://localhost:8000/api/regions/upload"
                    res = requests.post(upload_url, data=data, files=files, headers=headers, timeout=15)
                    if res.status_code == 200:
                        st.session_state["parsed_batch"] = res.json()
                        st.success("Phase A (분석) 완료! 우측 화면에서 검증된 스키마와 데이터 프리뷰를 확인하세요.")
                        st.rerun()
                    else:
                        st.error(f"분석 실패: {res.text}")
                except Exception as e:
                    st.error(f"분석 중 연결 실패: {e}")

    with col2:
        # 만약 분석된 임시 배치 데이터(Phase A)가 세션에 있다면 프리뷰 및 확정 커밋 화면 제공
        if "parsed_batch" in st.session_state:
            batch = st.session_state["parsed_batch"]
            batch_id = batch.get("batchId")
            drift_score = batch.get("driftScore", 0.0)
            quality_score = batch.get("qualityScore", 0.0)
            detected_mapping = batch.get("mapping", {})
            preview_rows = batch.get("previewRows", [])

            st.markdown('<div class="sec">2단계: 데이터 프리뷰 및 매핑 보정 (Phase B)</div>', unsafe_allow_html=True)

            # 신뢰도 등급에 맞는 색상 설정
            drift_color = "g" if drift_score < 0.2 else ("y" if drift_score <= 0.5 else "r")
            quality_color = "g" if quality_score >= 0.85 else ("y" if quality_score >= 0.55 else "r")

            st.markdown(f'''<div class="kg">
            <div class="kc"><div class="kl">배치 ID</div><div class="kv b" style="font-size:12px; font-weight:bold;">{batch_id}</div><div class="ku">임시 트랜잭션 식별자</div></div>
            <div class="kc"><div class="kl">스키마 드리프트</div><div class="kv {drift_color}">{drift_score:.2f}</div><div class="ku">낮을수록 정밀함</div></div>
            <div class="kc"><div class="kl">데이터 무결성 품질</div><div class="kv {quality_color}">{quality_score * 100:.1f}%</div><div class="ku">유효 행 비중</div></div>
            <div class="kc"><div class="kl">검증된 행 수</div><div class="kv g">{len(preview_rows)} 건</div><div class="ku">스테이징 완료</div></div>
            </div>''', unsafe_allow_html=True)

            # SCM 의미론적 컬럼 수동 보정 (st.data_editor 사용)
            st.markdown("#### ⚙️ 의미론적 컬럼 스키마 수동 매핑 교정")
            mapping_list = []
            for excel_col, std_col in detected_mapping.items():
                mapping_list.append({
                    "엑셀 내 컬럼명": excel_col,
                    "감지된 SCM 표준 컬럼": std_col if std_col else "미정(무시)"
                })
            
            df_mapping = pd.DataFrame(mapping_list)
            edited_df = st.data_editor(
                df_mapping,
                column_config={
                    "감지된 SCM 표준 컬럼": st.column_config.SelectboxColumn(
                        "SCM 표준 컬럼 보정",
                        help="SCM 데이터베이스 스키마와 매핑할 표준 컬럼을 선택하세요.",
                        options=["region_code", "product_name", "date", "quantity", "미정(무시)"],
                        required=True
                    )
                },
                disabled=["엑셀 내 컬럼명"],
                key="schema_mapping_editor",
                use_container_width=True
            )

            # 행 단위 검증 상태 프리뷰 테이블 렌더링
            st.markdown("#### 👁️ 행 단위 상세 검증 및 정합성 프리뷰")
            if preview_rows:
                df_rows = pd.DataFrame(preview_rows)
                # 이모지 상태 맵 장착
                df_rows["상태"] = df_rows["validationStatus"].apply(lambda s: "🟢 VALID" if s == "VALID" else "🔴 INVALID")
                
                # 열 재배치 및 컬럼 한글화
                df_rows_show = df_rows[["sourceRowIndex", "regionCode", "productName", "date", "quantity", "상태"]].rename(columns={
                    "sourceRowIndex": "엑셀 행 번호",
                    "regionCode": "지역 코드",
                    "productName": "품목명",
                    "date": "기준 일자",
                    "quantity": "수량",
                })
                st.dataframe(df_rows_show, use_container_width=True)
            else:
                st.info("💡 검증된 행 데이터가 존재하지 않습니다.")

            # 최종 Commit / Cancel 버튼 렌더링
            c_btn1, c_btn2 = st.columns([1, 1])
            with c_btn1:
                if st.button("📥 AI 매핑 확인 및 최종 DB 반영 (Commit)", key="btn_confirm_commit", type="primary"):
                    # 보정된 매핑 딕셔너리 생성
                    user_overrides = {}
                    for idx, row in edited_df.iterrows():
                        excel_col = row["엑셀 내 컬럼명"]
                        std_col = row["감지된 SCM 표준 컬럼"]
                        user_overrides[excel_col] = std_col if std_col != "미정(무시)" else None

                    # Phase B confirm API 호출
                    headers = {"Authorization": f"Bearer {st.session_state['access_token']}"}
                    try:
                        confirm_url = f"{auth_helper.API_BASE_URL}/api/regions/upload/confirm?batch_id={batch_id}"
                        if st.session_state.get("use_mock_fallback"):
                            confirm_url = f"http://localhost:8000/api/regions/upload/confirm?batch_id={batch_id}"
                        res = requests.post(confirm_url, json=user_overrides, headers=headers, timeout=15)
                        if res.status_code == 200:
                            data = res.json()
                            st.success(f"🎉 최종 DB 적재 완료! 총 {data.get('committedCount', 0)}건의 무결한 데이터가 실재고(RegionInventory) 테이블에 반영되었습니다.")
                            st.session_state.pop("parsed_batch", None)
                            st.balloons()
                            st.rerun()
                        else:
                            st.error(f"최종 커밋 실패: {res.text}")
                    except Exception as e:
                        st.error(f"최종 커밋 중 백엔드 연결 실패: {e}")

            with c_btn2:
                if st.button("❌ 업로드 취소 (Rollback)", key="btn_cancel_commit"):
                    st.session_state.pop("parsed_batch", None)
                    st.info("임시 업로드 배치가 파기되었습니다.")
                    st.rerun()

        else:
            # 기본 실시간 지역 재고 흐름 & 기상 융합 분석 화면 렌더링
            st.markdown('<div class="sec">실시간 지역 재고 흐름 & 기상 융합 분석</div>', unsafe_allow_html=True)

            inv_data = auth_helper.api_get(f"/api/dashboard/region/{selected_region['regionCode']}/inventory")
            if not inv_data:
                st.info("💡 분석을 진행하기 위해 좌측 패널에서 재고 데이터를 업로드해 주세요.")
                return

            inv_df = pd.DataFrame([
                {
                    "product_name": inv["id"]["productName"],
                    "date": inv["id"]["date"],
                    "quantity": inv["quantity"]
                } for inv in inv_data
            ])

            weather_data = auth_helper.api_get(f"/api/dashboard/region/{selected_region['regionCode']}/weather")
            weather_df = pd.DataFrame(weather_data) if weather_data else pd.DataFrame()

            products = inv_df["product_name"].unique()
            total_qty = inv_df.groupby("product_name")["quantity"].last().sum()

            st.markdown(f'''<div class="kg">
            <div class="kc"><div class="kl">모니터링 품목수</div><div class="kv">{len(products)} SKU</div><div class="ku">지정 품목 리스트</div></div>
            <div class="kc"><div class="kl">최신 총 재고량</div><div class="kv b">{total_qty:,.0f}</div><div class="ku">units (마지막 일자 기준)</div></div>
            <div class="kc"><div class="kl">기상 관측일수</div><div class="kv g">{len(weather_df)}일</div><div class="ku">동기화 완료</div></div>
            </div>''', unsafe_allow_html=True)

            selected_prod = st.selectbox("분석할 품목 선택", options=products)
            prod_inv = inv_df[inv_df["product_name"] == selected_prod]

            st.markdown(f'<div class="cc"><div class="ct"><span class="dt" style="background:#8ab4f8"></span>[{selected_prod}] 일별 재고 변동 추이</div>', unsafe_allow_html=True)
            
            fig, ax = plt.subplots(figsize=(10, 2.5), dpi=100)
            fig.patch.set_facecolor(BG)
            ax.set_facecolor(BG)
            
            dates_parsed = pd.to_datetime(prod_inv["date"])
            ax.plot(dates_parsed, prod_inv["quantity"], color="#8ab4f8", lw=1.6, label="재고량")
            ax.fill_between(dates_parsed, prod_inv["quantity"], alpha=0.08, color="#8ab4f8")
            
            sax(ax)
            ax.set_xlabel("날짜 (Date)", fontsize=8, color=TX)
            ax.set_ylabel("수량 (Units)", fontsize=8, color=TX)
            fig.tight_layout(pad=0.5)
            st.pyplot(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="sec">재고 효율성 및 데이터 무결성 관제탑</div>', unsafe_allow_html=True)
            latest_date = prod_inv["date"].iloc[-1]
            
            integrity_result = auth_helper.api_get(f"/api/dashboard/region/{selected_region['regionCode']}/integrity?product={selected_prod}&date={latest_date}")
            if integrity_result:
                if integrity_result.get("isConsistent", True):
                    st.success(f"✅ 데이터 무결성 검증 완료 | {integrity_result.get('message')}")
                else:
                    st.error(f"⚠️ 무결성 불일치 발생 | {integrity_result.get('message')}")

if __name__ == "__main__":
    show()
