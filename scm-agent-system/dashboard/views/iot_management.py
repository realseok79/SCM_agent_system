# dashboard/views/iot_management.py
import streamlit as st
import pandas as pd
import auth_helper

from components.styles import inject_custom_css

def render_iot_management():
    # 1. 권한 검증 (ROLE_ADMIN 만 접근 허용)
    user_role = st.session_state.get("user_role", "ROLE_USER")
    if user_role != "ROLE_ADMIN":
        st.error("🚨 권한 오류: 이 페이지는 관리자(ROLE_ADMIN)만 접근할 수 있습니다.")
        return

    inject_custom_css()
    st.markdown(f'<div class="hdr"><div><div class="hdr-t">IoT 센서 모니터링 (REST 연동)</div><div class="hdr-s">물류 창고 실시간 IoT 센서 디바이스 등록 및 활성 상태 중앙 관리 통제탑</div></div></div>', unsafe_allow_html=True)

    # 2. 지역 정보 가져오기 (디바이스 등록 시 매핑할 지역 목록)
    regions = auth_helper.api_get("/api/regions") or []
    region_options = {f"{r['regionName']} ({r['regionCode']})": r['regionCode'] for r in regions}

    col_list, col_reg = st.columns([2, 1])

    with col_reg:
        st.markdown('<div class="sec">신규 IoT 디바이스 등록</div>', unsafe_allow_html=True)
        with st.form("register_device_form"):
            dev_id = st.text_input("디바이스 ID (예: SENS-TEMP-001)", placeholder="SENS-TEMP-xxx")
            
            if region_options:
                selected_region_label = st.selectbox("연동 지점", list(region_options.keys()))
                region_code = region_options[selected_region_label]
            else:
                st.warning("⚠️ 등록된 지점이 없어 디바이스를 매핑할 수 없습니다.")
                region_code = None
                
            sensor_type = st.selectbox("센서 유형", ["temperature", "humidity", "vibration", "rfid_count"])
            
            submit_btn = st.form_submit_button("디바이스 등록")
            
            if submit_btn:
                if not dev_id.strip():
                    st.error("디바이스 ID를 입력해주세요.")
                elif not region_code:
                    st.error("연동 지점을 선택해야 합니다.")
                else:
                    payload = {
                        "deviceId": dev_id.strip(),
                        "regionCode": region_code,
                        "sensorType": sensor_type,
                        "status": "ACTIVE"
                    }
                    res = auth_helper.api_post("/api/iot/devices", payload)
                    if res:
                        st.success(f"디바이스 {dev_id} 등록 성공!")
                        st.rerun()

    with col_list:
        st.markdown('<div class="sec">IoT 센서 상태 목록</div>', unsafe_allow_html=True)
        
        # 3. 디바이스 목록 가져오기
        devices = auth_helper.api_get("/api/iot/devices")
        
        if not devices:
            st.info("등록된 IoT 센서 디바이스가 없습니다. 우측 폼을 이용해 첫 디바이스를 등록하세요.")
        else:
            # Table visualization
            df_data = []
            for dev in devices:
                df_data.append({
                    "디바이스 ID": dev.get("deviceId"),
                    "지점 코드": dev.get("regionCode"),
                    "센서 유형": dev.get("sensorType"),
                    "상태": "🟢 ACTIVE" if dev.get("status") == "ACTIVE" else "🛠️ MAINTENANCE",
                    "마지막 수신 시간": dev.get("lastPingAt") or "수신 기록 없음"
                })
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True)

            st.markdown('<div class="sec" style="margin-top: 20px;">장비 상태 원격 토글</div>', unsafe_allow_html=True)
            
            # Show individual devices with toggles
            for dev in devices:
                d_id = dev.get("deviceId")
                curr_status = dev.get("status")
                
                c1, c2, c3 = st.columns([2, 1, 1])
                c1.write(f"**{d_id}** ({dev.get('sensorType')} - {dev.get('regionCode')})")
                c2.write(f"상태: `{'ACTIVE' if curr_status == 'ACTIVE' else 'MAINTENANCE'}`")
                
                target_status = "MAINTENANCE" if curr_status == "ACTIVE" else "ACTIVE"
                btn_label = "🛠️ 점검 전환" if curr_status == "ACTIVE" else "🟢 가동 전환"
                
                if c3.button(btn_label, key=f"toggle_{d_id}"):
                    patch_payload = {"status": target_status}
                    res = auth_helper.api_patch(f"/api/iot/devices/{d_id}/status", patch_payload)
                    if res:
                        st.success(f"{d_id} 상태가 {target_status}로 변경되었습니다.")
                        st.rerun()
