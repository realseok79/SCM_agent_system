# dashboard/views/regional/main_view.py
import streamlit as st
import auth_helper
from components.styles import inject_custom_css
from .crud_tab import render_region_crud
from .upload_tab import render_data_upload
from .chart_tab import render_regional_charts

def render_regional_dashboard():
    inject_custom_css()
    st.markdown(f'<div class="hdr"><div><div class="hdr-t">지역별 SCM 관제 센터 (REST 연동)</div><div class="hdr-s">지역별 재고 CRUD 및 기상 융합 인공지능 분석 관제탑</div></div></div>', unsafe_allow_html=True)

    # 1. 지역 조회
    regions_res = auth_helper.api_get("/api/regions")
    if regions_res is None:
        st.warning("지역 정보를 읽어오지 못했습니다. (네트워크 상태 확인 필요)")
        regions = []
    else:
        regions = regions_res

    col1, col2 = st.columns([1, 2.2])

    # 2. 사용자 권한 조회
    user_role = st.session_state.get("user_role", "ROLE_USER")
    region_options = {f"{r['regionName']} ({r['regionCode']})": r for r in regions} if regions else {}

    with col1:
        # CRUD operations
        render_region_crud(regions, region_options, user_role)
        
        # Region selection
        selected_region = None
        if regions:
            region_options_keys = list(region_options.keys())
            
            if "auto_selected_region" in st.session_state:
                target_code = st.session_state["auto_selected_region"]
                for k in region_options_keys:
                    if region_options[k]["regionCode"] == target_code:
                        st.session_state["selected_region_name"] = k
                        break
                del st.session_state["auto_selected_region"]
                
            if "selected_region_name" not in st.session_state or st.session_state["selected_region_name"] not in region_options:
                st.session_state["selected_region_name"] = region_options_keys[0]

            selected_key = st.selectbox(
                "관제할 지역 선택", 
                options=region_options_keys, 
                key="selected_region_name"
            )
            selected_region = region_options[selected_key]
            st.session_state["active_region_code"] = selected_region['regionCode']
            st.session_state["active_region_name"] = selected_region['regionName']

            st.markdown(f"""
            <div class="kc" style="margin-bottom: 10px;">
                <div class="kl">선택된 지역 코드</div>
                <div class="kv b">{selected_region['regionCode']}</div>
                <div class="ku">{selected_region['description'] or '설명 없음'}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("등록된 지역이 없습니다. 아래에서 SCM 엑셀/CSV 파일을 업로드하면 자동으로 지역이 등록됩니다.")

        # Data upload and mapping editor
        render_data_upload(user_role)

    with col2:
        # Charts and analytics
        render_regional_charts(selected_region)
