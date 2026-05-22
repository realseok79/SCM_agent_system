# dashboard/pages/regional.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests
import auth_helper
from components.styles import BG, TX, sax

def render_regional_dashboard():
    st.markdown(f'<div class="hdr"><div><div class="hdr-t">지역별 SCM 관제 센터 (REST 연동)</div><div class="hdr-s">지역별 재고 CRUD 및 기상 융합 인공지능 분석 관제탑</div></div></div>', unsafe_allow_html=True)

    # 지역 조회
    regions = auth_helper.api_get("/api/regions")
    if regions is None:
        st.warning("⚠️ 지역 정보를 읽어오지 못했습니다.")
        return

    col1, col2 = st.columns([1, 2.2])

    # 사용자 권한 조회
    user_role = st.session_state.get("user_role", "ROLE_USER")

    with col1:
        st.markdown('<div class="sec">지역 관리 & 데이터 수집</div>', unsafe_allow_html=True)
        
        region_options = {f"{r['regionName']} ({r['regionCode']})": r for r in regions} if regions else {}
        
        if user_role == "ROLE_EXECUTIVE":
            st.info("🔒 경영진 계정은 거점 등록/삭제 권한이 없습니다.")
        else:
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
                                "regionCode": new_name, # standardizer가 변환함
                                "description": new_desc
                            }
                            res = auth_helper.api_post("/api/regions", payload)
                            if res:
                                st.success("지역이 성공적으로 등록되었습니다.")
                                st.rerun()
                            else:
                                st.error("지역 등록 실패")

            # 등록 지역 삭제
            with st.expander("❌ 등록 지역 삭제", expanded=False):
                if not regions:
                    st.info("삭제할 수 있는 지역이 없습니다.")
                else:
                    with st.form("delete_region_form"):
                        delete_target_key = st.selectbox("삭제할 지역 선택", options=list(region_options.keys()), key="delete_region_select")
                        delete_btn = st.form_submit_button("지역 삭제")
                        
                        if delete_btn:
                            delete_target = region_options[delete_target_key]
                            res = auth_helper.api_delete(f"/api/regions/{delete_target['id']}")
                            if res:
                                st.success(f"[{delete_target['regionName']}] 지역이 성공적으로 삭제되었습니다.")
                                if st.session_state.get("selected_region_name") == delete_target_key:
                                    st.session_state.pop("selected_region_name", None)
                                st.rerun()
                            else:
                                st.error("지역 삭제 실패")

        if not regions:
            st.warning("⚠️ 등록된 지역이 없습니다. 먼저 지역을 등록해 주세요.")
            return
        
        # 기본 선택값 결정 (신규 등록/파싱 지역 우선 자동 선택)
        region_options_keys = list(region_options.keys())
        
        if "auto_selected_region" in st.session_state:
            target_code = st.session_state["auto_selected_region"]
            for k in region_options_keys:
                if region_options[k]["regionCode"] == target_code:
                    st.session_state["selected_region_name"] = k
                    break
            # 한 번 사용한 세션 값은 삭제
            del st.session_state["auto_selected_region"]
            
        if "selected_region_name" not in st.session_state or st.session_state["selected_region_name"] not in region_options:
            st.session_state["selected_region_name"] = region_options_keys[0]

        selected_key = st.selectbox(
            "관제할 지역 선택", 
            options=region_options_keys, 
            key="selected_region_name"
        )
        selected_region = region_options[selected_key]

        st.markdown(f"""
        <div class="kc" style="margin-bottom: 10px;">
            <div class="kl">선택된 지역 코드</div>
            <div class="kv b">{selected_region['regionCode']}</div>
            <div class="ku">{selected_region['description'] or '설명 없음'}</div>
        </div>
        """, unsafe_allow_html=True)

        # 데이터 업로드
        st.markdown('<div class="sec">SCM 엑셀/CSV 데이터 업로드</div>', unsafe_allow_html=True)
        if user_role == "ROLE_EXECUTIVE":
            st.warning("🔒 경영진 계정은 SCM 원천 데이터를 업로드할 권한이 없습니다.")
        else:
            uploaded_file = st.file_uploader("지역 재고 및 수요 이력 업로드", type=["csv", "xlsx", "xls"], key="regional_uploader")
            
            if uploaded_file is not None:
                if "analyze_result" not in st.session_state or st.session_state.get("analyze_file_name") != uploaded_file.name:
                    with st.spinner("⚡ AI (Gemini 3.1 Flash-Lite)가 엑셀의 시트와 헤더 시작점을 지능적으로 탐색하는 중입니다..."):
                        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                        try:
                            res = requests.post("http://localhost:8090/analyze/excel/llm", files=files, timeout=30)
                            if res.status_code == 200:
                                st.session_state["analyze_result"] = res.json()
                                st.session_state["analyze_file_bytes"] = uploaded_file.getvalue()
                                st.session_state["analyze_file_name"] = uploaded_file.name
                                st.session_state["analyze_file_type"] = uploaded_file.type
                                st.rerun()
                            else:
                                st.error(f"❌ 데이터 분석 실패: {res.text}")
                        except Exception as e:
                            st.error(f"❌ 분석 서버 연결 실패: {e}")
            else:
                st.session_state.pop("analyze_result", None)
                st.session_state.pop("analyze_file_bytes", None)
                st.session_state.pop("analyze_file_name", None)
                st.session_state.pop("analyze_file_type", None)

            if "analyze_result" in st.session_state:
                res_json = st.session_state["analyze_result"]
                drift = res_json.get("driftScore", 0.0)
                quality = res_json.get("qualityScore", 1.0)
                mapping = res_json.get("mapping", {})
                
                st.markdown("### 🔍 AI 스키마 매핑 및 검증 프리뷰")
                
                # 지표 렌더링
                met_col1, met_col2 = st.columns(2)
                with met_col1:
                    if drift >= 0.2:
                        st.metric("⚠️ 스키마 드리프트 점수", f"{drift:.3f}", delta="경고: 비표준 헤더", delta_color="inverse")
                    else:
                        st.metric("✅ 스키마 드리프트 점수", f"{drift:.3f}", delta="정상: 규격 적합")
                with met_col2:
                    if quality < 0.9:
                        st.metric("⚠️ 데이터 정합성 점수", f"{quality*100:.1f}%", delta="일부 행 경고/오류", delta_color="inverse")
                    else:
                        st.metric("✅ 데이터 정합성 점수", f"{quality*100:.1f}%", delta="정상 데이터")

                # 미매핑 경고
                unmapped_cols = [k for k, v in mapping.items() if not v]
                if unmapped_cols:
                    st.warning(f"🔴 **수동 매핑 필요**: SCM 표준 열에 매핑되지 않은 원본 헤더가 존재합니다: `{', '.join(unmapped_cols)}`")
                
                # 데이터 매핑 수동 편집기 (st.data_editor)
                st.write("📋 **컬럼 매핑 확인 및 조정**")
                mapping_data = []
                for raw_col, std_col in mapping.items():
                    mapping_data.append({
                        "원본 컬럼": raw_col,
                        "표준 SCM 컬럼 매핑": std_col if std_col else "미매핑"
                    })
                df_mapping = pd.DataFrame(mapping_data)
                
                edited_df = st.data_editor(
                    df_mapping,
                    column_config={
                        "표준 SCM 컬럼 매핑": st.column_config.SelectboxColumn(
                            "표준 SCM 컬럼 매핑",
                            help="원본 엑셀 컬럼이 표준 SCM 데이터 규격의 어떤 열에 해당하는지 매핑합니다.",
                            options=["region_code", "product_name", "date", "quantity", "미매핑"],
                            required=True,
                            width="medium"
                        )
                    },
                    disabled=["원본 컬럼"],
                    use_container_width=True,
                    key="mapping_editor"
                )
                
                # 데이터 미리보기
                st.write("📄 **데이터 일부 프리뷰 (최대 10행)**")
                preview_df = pd.DataFrame(res_json.get("previewRows", []), columns=res_json.get("columns", []))
                st.dataframe(preview_df, use_container_width=True)

                # 승인/반영 단추
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("🚀 AI 매핑 승인 및 최종 반영", use_container_width=True, type="primary"):
                        confirmed_mapping = {}
                        for _, r in edited_df.iterrows():
                            raw = r["원본 컬럼"]
                            std = r["표준 SCM 컬럼 매핑"]
                            confirmed_mapping[raw] = None if std == "미매핑" else std
                        
                        with st.spinner("⚡ AI 데이터 클렌징 및 최종 재고 반영 중..."):
                            import json
                            try:
                                # 1단계: FastAPI를 통한 비정형 데이터 정제 및 병합 (Clean)
                                clean_files = {"file": (st.session_state["analyze_file_name"], st.session_state["analyze_file_bytes"], st.session_state["analyze_file_type"])}
                                clean_data = {"user_mapping": json.dumps(confirmed_mapping)}
                                clean_res = requests.post("http://localhost:8090/clean/excel", files=clean_files, data=clean_data, timeout=25)
                                
                                if clean_res.status_code != 200:
                                    st.error(f"❌ AI 데이터 클렌징 실패: {clean_res.text}")
                                else:
                                    cleaned_csv_str = clean_res.json().get("cleaned_csv", "")
                                    
                                    # 2단계: 정제 완료된 완전 표준 규격 CSV를 Java 백엔드에 다이렉트 전송
                                    files = {"file": ("cleaned_data.csv", cleaned_csv_str.encode("utf-8"), "text/csv")}
                                    data = {
                                        "company_id": "SIGMA",
                                        "user_mapping": json.dumps({
                                            "region_code": "region_code",
                                            "product_name": "product_name",
                                            "date": "date",
                                            "quantity": "quantity"
                                        })
                                    }
                                    headers = {"Authorization": f"Bearer {st.session_state['access_token']}"}
                                    
                                    confirm_res = requests.post(
                                        f"{auth_helper.API_BASE_URL}/api/regions/upload/confirm",
                                        data=data,
                                        files=files,
                                        headers=headers,
                                        timeout=15
                                    )
                                    if confirm_res.status_code == 200:
                                        st.session_state["upload_success"] = True
                                        res_json_confirm = confirm_res.json()
                                        new_regs = res_json_confirm.get("newlyRegisteredRegions", [])
                                        proc_regs = res_json_confirm.get("processedRegions", [])
                                        if new_regs:
                                            st.session_state["auto_selected_region"] = new_regs[0]
                                        elif proc_regs:
                                            st.session_state["auto_selected_region"] = proc_regs[0]
                                        
                                        # 세션 정리
                                        st.session_state.pop("analyze_result", None)
                                        st.session_state.pop("analyze_file_bytes", None)
                                        st.session_state.pop("analyze_file_name", None)
                                        st.session_state.pop("analyze_file_type", None)
                                        st.rerun()
                                    else:
                                        st.error(f"❌ 최종 반영 실패: {confirm_res.text}")
                            except Exception as e:
                                st.error(f"❌ 반영 서버 통신 실패: {e}")
                
                with col_btn2:
                    if st.button("❌ 매핑 작업 취소", use_container_width=True):
                        st.session_state.pop("analyze_result", None)
                        st.session_state.pop("analyze_file_bytes", None)
                        st.session_state.pop("analyze_file_name", None)
                        st.session_state.pop("analyze_file_type", None)
                        st.rerun()

            if st.session_state.get("upload_success"):
                st.success("데이터 업로드 및 최종 반영이 완벽하게 완료되었습니다.")
                del st.session_state["upload_success"]

    with col2:
        st.markdown('<div class="sec">실시간 지역 재고 흐름 & 기상 융합 분석</div>', unsafe_allow_html=True)

        # 1. 해당 지역 재고 데이터 조회
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

        # 2. 기상 데이터 조회
        weather_data = auth_helper.api_get(f"/api/dashboard/region/{selected_region['regionCode']}/weather")
        weather_df = pd.DataFrame(weather_data) if weather_data else pd.DataFrame()

        # 재고 KPI 카드 렌더링
        # 물량이 없는(최신 재고량이 0 이하인) 품목 제외
        inv_df["quantity"] = pd.to_numeric(inv_df["quantity"], errors="coerce").fillna(0)
        
        active_products = []
        for p in inv_df["product_name"].unique():
            p_df = inv_df[inv_df["product_name"] == p].sort_values("date")
            if not p_df.empty and p_df["quantity"].iloc[-1] > 0:
                active_products.append(p)
                
        products = active_products
        
        if not products:
            st.info("💡 분석할 만한 유효 재고(최신 물량 > 0)를 가진 품목이 없습니다.")
            return
            
        total_qty = inv_df[inv_df["product_name"].isin(products)].groupby("product_name")["quantity"].last().sum()

        st.markdown(f'''<div class="kg">
        <div class="kc"><div class="kl">모니터링 품목수</div><div class="kv">{len(products)} SKU</div><div class="ku">지정 품목 리스트</div></div>
        <div class="kc"><div class="kl">최신 총 재고량</div><div class="kv b">{total_qty:,.0f}</div><div class="ku">units (마지막 일자 기준)</div></div>
        <div class="kc"><div class="kl">기상 관측일수</div><div class="kv g">{len(weather_df)}일</div><div class="ku">동기화 완료</div></div>
        </div>''', unsafe_allow_html=True)

        # 품목 선택 필터
        selected_prod = st.selectbox("분석할 품목 선택", options=products)
        prod_inv = inv_df[inv_df["product_name"] == selected_prod]

        # 1. 재고 변동 차트 시각화 및 2. 데이터 무결성 검증
        if prod_inv.empty or prod_inv["quantity"].iloc[-1] <= 0:
            st.info(f"💡 [{selected_prod}] 품목은 현재 재고가 없어 차트 및 무결성 분석을 제공하지 않습니다.")
        else:
            st.markdown(f'<div class="cc"><div class="ct"><span class="dt" style="background:#8ab4f8"></span>[{selected_prod}] 일별 재고 변동 추이</div>', unsafe_allow_html=True)
            
            fig, ax = plt.subplots(figsize=(10, 2.5), dpi=100)
            fig.patch.set_facecolor(BG)
            ax.set_facecolor(BG)
            
            dates_parsed = pd.to_datetime(prod_inv["date"])
            prod_inv = prod_inv.assign(parsed_date=dates_parsed)
            prod_inv = prod_inv.sort_values("parsed_date")
            
            ax.plot(prod_inv["parsed_date"], prod_inv["quantity"], color="#8ab4f8", lw=1.6, marker="o", label="재고량")
            ax.fill_between(prod_inv["parsed_date"], prod_inv["quantity"], alpha=0.08, color="#8ab4f8")
            
            sax(ax)
            ax.set_xlabel("날짜 (Date)", fontsize=8, color=TX)
            ax.set_ylabel("수량 (Units)", fontsize=8, color=TX)
            fig.tight_layout(pad=0.5)
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)
            st.markdown('</div>', unsafe_allow_html=True)

            # 2. 데이터 무결성 검증
            st.markdown('<div class="sec">재고 효율성 및 데이터 무결성 관제탑</div>', unsafe_allow_html=True)
            latest_date = prod_inv["date"].iloc[-1]
            
            # 무결성 검증 API 호출
            integrity_result = auth_helper.api_get(f"/api/dashboard/region/{selected_region['regionCode']}/integrity?product={selected_prod}&date={latest_date}")
            if integrity_result:
                if integrity_result.get("isConsistent", True):
                    st.success(f"✅ 데이터 무결성 검증 완료 | {integrity_result.get('message')}")
                else:
                    st.error(f"⚠️ 무결성 불일치 발생 | {integrity_result.get('message')}")
