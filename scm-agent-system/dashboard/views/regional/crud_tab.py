# dashboard/views/regional/crud_tab.py
import streamlit as st
import auth_helper

def render_region_crud(regions, region_options, user_role):
    st.markdown('<div class="sec">지역 관리 & 데이터 수집</div>', unsafe_allow_html=True)
    if st.session_state.get("is_offline", False):
        st.warning("⚠️ 시스템이 오프라인 모드입니다. 신규 지점 등록 및 삭제 기능이 비활성화됩니다.")
        return
    
    if user_role == "ROLE_EXECUTIVE":
        st.info("경영진 계정은 거점 등록/삭제 권한이 없습니다.")
    else:
        # 신규 지역 등록
        with st.expander("신규 지역 등록", expanded=False):
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
        with st.expander("등록 지역 삭제", expanded=False):
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
