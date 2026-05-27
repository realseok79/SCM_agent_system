# dashboard/views/regional/upload_tab.py
import streamlit as st
import pandas as pd
import requests
import os
import json
import auth_helper

ANALYSIS_SERVICE_URL = os.getenv("ANALYSIS_SERVICE_URL", "http://localhost:8090")

def render_data_upload(user_role):
    st.markdown('<div class="sec">SCM 엑셀/CSV 데이터 업로드</div>', unsafe_allow_html=True)
    if st.session_state.get("is_offline", False):
        st.error("⚠️ 시스템이 오프라인 모드입니다. SCM 데이터 업로드가 비활성화됩니다.")
        return
    if user_role == "ROLE_EXECUTIVE":
        st.warning("경영진 계정은 SCM 원천 데이터를 업로드할 권한이 없습니다.")
        return
        
    uploaded_file = st.file_uploader("지역 재고 및 수요 이력 업로드", type=["csv", "xlsx", "xls"], key="regional_uploader")
    
    if uploaded_file is not None:
        if "analyze_result" not in st.session_state or st.session_state.get("analyze_file_name") != uploaded_file.name:
            with st.spinner("AI가 엑셀의 시트와 헤더 시작점을 지능적으로 탐색하는 중입니다..."):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                try:
                    res = requests.post(f"{ANALYSIS_SERVICE_URL}/analyze/excel/llm", files=files, timeout=30)
                    if res.status_code == 200:
                        st.session_state["analyze_result"] = res.json()
                        st.session_state["analyze_file_bytes"] = uploaded_file.getvalue()
                        st.session_state["analyze_file_name"] = uploaded_file.name
                        st.session_state["analyze_file_type"] = uploaded_file.type
                        st.rerun()
                    else:
                        st.error(f"데이터 분석 실패: {res.text}")
                except Exception as e:
                    st.error(f"분석 서버 연결 실패: {e}")
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
        
        st.markdown("### AI 스키마 매핑 및 검증 프리뷰")
        
        # 지표 렌더링
        met_col1, met_col2 = st.columns(2)
        with met_col1:
            if drift >= 0.2:
                st.metric(" 스키마 드리프트 점수", f"{drift:.3f}", delta="경고: 비표준 헤더", delta_color="inverse")
            else:
                st.metric("스키마 드리프트 점수", f"{drift:.3f}", delta="정상: 규격 적합")
        with met_col2:
            if quality < 0.9:
                st.metric(" 데이터 정합성 점수", f"{quality*100:.1f}%", delta="일부 행 경고/오류", delta_color="inverse")
            else:
                st.metric("데이터 정합성 점수", f"{quality*100:.1f}%", delta="정상 데이터")

        # 미매핑 경고
        unmapped_cols = [k for k, v in mapping.items() if not v]
        if unmapped_cols:
            st.warning(f" **수동 매핑 필요**: SCM 표준 열에 매핑되지 않은 원본 헤더가 존재합니다: `{', '.join(unmapped_cols)}`")
        
        # 데이터 매핑 수동 편집기
        st.write("컬럼 매핑 확인 및 조정")
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
        st.write("데이터 일부 프리뷰 (최대 10행)")
        preview_df = pd.DataFrame(res_json.get("previewRows", []), columns=res_json.get("columns", []))
        st.dataframe(preview_df, use_container_width=True)

        # validation for region_code
        has_region_code = any(edited_df["표준 SCM 컬럼 매핑"] == "region_code")
        if not has_region_code:
            st.warning(" 신규 지역 자동 등록을 위해 지역을 구분할 수 있는 컬럼(region_code)을 반드시 매핑해주세요.")

        # 승인/반영 단추
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("AI 매핑 승인 및 최종 반영", use_container_width=True, type="primary"):
                if not has_region_code:
                    st.error("지역 코드(region_code) 매핑이 누락되었습니다. 반영을 중단합니다.")
                else:
                    confirmed_mapping = {}
                    for _, r in edited_df.iterrows():
                        raw = r["원본 컬럼"]
                        std = r["표준 SCM 컬럼 매핑"]
                        confirmed_mapping[raw] = None if std == "미매핑" else std
                    
                    with st.spinner("AI 데이터 클렌징 및 최종 재고 반영 중..."):
                        try:
                            # 1단계: FastAPI를 통한 비정형 데이터 정제 및 병합 (Clean)
                            clean_files = {"file": (st.session_state["analyze_file_name"], st.session_state["analyze_file_bytes"], st.session_state["analyze_file_type"])}
                            clean_data = {"user_mapping": json.dumps(confirmed_mapping)}
                            clean_res = requests.post(f"{ANALYSIS_SERVICE_URL}/clean/excel", files=clean_files, data=clean_data, timeout=25)
                            
                            if clean_res.status_code != 200:
                                st.error(f"AI 데이터 클렌징 실패: {clean_res.text}")
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
                                    st.error(f"최종 반영 실패: {confirm_res.text}")
                        except Exception as e:
                            st.error(f"반영 서버 통신 실패: {e}")
        
        with col_btn2:
            if st.button("매핑 작업 취소", use_container_width=True):
                st.session_state.pop("analyze_result", None)
                st.session_state.pop("analyze_file_bytes", None)
                st.session_state.pop("analyze_file_name", None)
                st.session_state.pop("analyze_file_type", None)
                st.rerun()

    if st.session_state.get("upload_success"):
        st.success("데이터 업로드 및 최종 반영이 완료되었습니다.")
        del st.session_state["upload_success"]
