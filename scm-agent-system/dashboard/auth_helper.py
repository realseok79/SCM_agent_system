# dashboard/auth_helper.py
import requests
import streamlit as st
import time
import os

# 중앙 API Base URL 설정 (기본값: 스프링 백엔드 포트 8080)
API_BASE_URL = st.sidebar.text_input("Backend API URL", "http://localhost:8080")

# SQLite 연결을 완전히 제거하고, 프론트 단독 작동(MOCK MODE)을 위한 인메모리 에뮬레이션 데이터베이스 구축 (단일 SSOT 확보 지침 준수)
MOCK_DATABASE = {
    "regions": [
        {"regionName": "Seoul Center", "regionCode": "SEOUL", "description": "수도권 통합 허브"},
        {"regionName": "Busan Port", "regionCode": "BUSAN", "description": "영남 및 수출입 관문"},
        {"regionName": "Incheon Air", "regionCode": "INCHEON", "description": "항공 물류 전초기지"}
    ],
    "region_inventory": [
        {"region_code": "SEOUL", "product_name": "마스크", "date": "2026-05-21", "quantity": 350.0},
        {"region_code": "SEOUL", "product_name": "마스크", "date": "2026-05-20", "quantity": 380.0},
        {"region_code": "SEOUL", "product_name": "마스크", "date": "2026-05-19", "quantity": 420.0},
        {"region_code": "SEOUL", "product_name": "마스크", "date": "2026-05-18", "quantity": 450.0},
        {"region_code": "SEOUL", "product_name": "마스크", "date": "2026-05-17", "quantity": 480.0},
        {"region_code": "SEOUL", "product_name": "마스크", "date": "2026-05-16", "quantity": 510.0},
        {"region_code": "SEOUL", "product_name": "마스크", "date": "2026-05-15", "quantity": 550.0},
        
        {"region_code": "BUSAN", "product_name": "반도체 칩", "date": "2026-05-21", "quantity": 70.0},
        {"region_code": "BUSAN", "product_name": "반도체 칩", "date": "2026-05-20", "quantity": 75.0},
        {"region_code": "BUSAN", "product_name": "반도체 칩", "date": "2026-05-19", "quantity": 82.0},
        {"region_code": "BUSAN", "product_name": "반도체 칩", "date": "2026-05-18", "quantity": 88.0},
        {"region_code": "BUSAN", "product_name": "반도체 칩", "date": "2026-05-17", "quantity": 95.0},
        {"region_code": "BUSAN", "product_name": "반도체 칩", "date": "2026-05-16", "quantity": 102.0},
        {"region_code": "BUSAN", "product_name": "반도체 칩", "date": "2026-05-15", "quantity": 110.0},
    ],
    "weather_cache": [
        {"region_code": "SEOUL", "date": "2026-05-21", "temp": 24.5, "humidity": 60.0, "precipitation": 0.0, "weather_desc": "맑음"},
        {"region_code": "BUSAN", "date": "2026-05-21", "temp": 18.0, "humidity": 85.0, "precipitation": 55.0, "weather_desc": "폭우"},
        {"region_code": "INCHEON", "date": "2026-05-21", "temp": 22.0, "humidity": 65.0, "precipitation": 0.0, "weather_desc": "구름 조금"}
    ],
    "regional_insights": [
        {"region_code": "SEOUL", "date": "2026-05-21", "action_plan_msg": "[Rule Engine] 지점 재고량(350개)이 ROP 안전재고 기준(400개) 대비 12.5% 미달하여 500개 자동 발주를 제안합니다."},
        {"region_code": "BUSAN", "date": "2026-05-21", "action_plan_msg": "[Rule Engine] 지점 재고량(70개)이 ROP 안전재고 기준(80개) 대비 12.5% 미달하여 100개 자동 발주를 제안합니다."}
    ],
    "purchase_orders": [
        {"id": 1, "region_code": "SEOUL", "product_name": "마스크", "quantity": 500.0, "status": "PENDING", "rejection_reason": None, "createdAt": "2026-05-21T11:00:00"},
        {"id": 2, "region_code": "BUSAN", "product_name": "반도체 칩", "quantity": 100.0, "status": "PENDING", "rejection_reason": None, "createdAt": "2026-05-21T11:05:00"}
    ],
    "product_financial_master": [
        {"product_name": "마스크", "unit_price": 1000.0, "holding_cost_per_day": 10.0},
        {"product_name": "반도체 칩", "unit_price": 50000.0, "holding_cost_per_day": 50.0}
    ],
    "order_feedback_log": [],
    "stock_out_logs": [
        {"id": 1, "region_code": "SEOUL", "product_name": "마스크", "date": "2026-05-18", "quantity": 20.0}
    ]
}

def api_login(username, password):
    """
    POST /api/auth/login 엔드포인트를 호출하여 토큰을 발급받고 st.session_state에 기록합니다.
    백엔드가 404이거나 오프라인일 때, admin/admin 계정인 경우 개발자 로컬 모드로 우회 접속을 보장합니다.
    """
    # 1. 원격 서버 접속 시도
    try:
        res = requests.post(f"{API_BASE_URL}/api/auth/login", json={
            "username": username,
            "password": password
        }, timeout=3)
        
        if res.status_code == 200:
            data = res.json()
            st.session_state["access_token"] = data["accessToken"]
            st.session_state["refresh_token"] = data["refreshToken"]
            st.session_state["user_role"] = data.get("role", "ROLE_USER")
            st.session_state["token_expires_at"] = time.time() + 1800
            st.session_state["use_mock_fallback"] = False
            return True, "Login successful"
    except Exception:
        pass  # 연결 실패 시 로컬 우회 모드로 자동 감지 진행

    # 2. 로컬 개발 환경용 바이패스 (스프링 백엔드 오프라인 시 자율 접속 보장)
    if username == "admin" and password == "admin":
        st.session_state["access_token"] = "mock_access_token_sigma_enterprise"
        st.session_state["refresh_token"] = "mock_refresh_token"
        st.session_state["user_role"] = "ROLE_ADMIN"
        st.session_state["token_expires_at"] = time.time() + 99999
        st.session_state["use_mock_fallback"] = True
        return True, "로컬 샌드박스 모드로 안전하게 로그인되었습니다. (인메모리 Mock 연동)"
        
    return False, "로그인 실패: 외부 스프링 백엔드 서버가 준비되지 않았으며, 로컬 마스터 비밀번호(admin/admin)와 일치하지 않습니다."

def api_refresh():
    if st.session_state.get("use_mock_fallback"):
        return True
    if "refresh_token" not in st.session_state:
        return False
    try:
        res = requests.post(f"{API_BASE_URL}/api/auth/refresh", json={
            "refreshToken": st.session_state["refresh_token"]
        }, timeout=3)
        if res.status_code == 200:
            data = res.json()
            st.session_state["access_token"] = data["accessToken"]
            st.session_state["refresh_token"] = data["refreshToken"]
            st.session_state["token_expires_at"] = time.time() + 1800
            return True
        else:
            api_logout()
            return False
    except Exception:
        return False

def api_logout():
    st.session_state.pop("access_token", None)
    st.session_state.pop("refresh_token", None)
    st.session_state.pop("user_role", None)
    st.session_state.pop("token_expires_at", None)
    st.session_state.pop("use_mock_fallback", None)

def check_auth_or_refresh():
    if "access_token" not in st.session_state:
        return False
    expires_at = st.session_state.get("token_expires_at", 0)
    if time.time() >= expires_at - 30:
        return api_refresh()
    return True

def api_get(endpoint):
    """
    인증 헤더를 포함해 GET 요청을 보냅니다.
    로컬 모드인 경우, 백엔드 API 대신 인메모리 MOCK_DATABASE를 통해 결과를 반환합니다.
    """
    if not check_auth_or_refresh():
        return None

    # ── [고도화] 로컬 샌드박스 모드 (인메모리 Mock) ──
    if st.session_state.get("use_mock_fallback"):
        return handle_local_get(endpoint)

    headers = {"Authorization": f"Bearer {st.session_state['access_token']}"}
    try:
        res = requests.get(f"{API_BASE_URL}{endpoint}", headers=headers, timeout=5)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        print(f"API GET {endpoint} failed: {e}")
    return None

def api_post(endpoint, payload):
    """
    인증 헤더를 포함해 POST 요청을 보냅니다.
    로컬 모드인 경우, 인메모리 MOCK_DATABASE에 INSERT/UPDATE를 반영합니다.
    """
    if not check_auth_or_refresh():
        return None

    # ── [고도화] 로컬 샌드박스 모드 (인메모리 Mock) ──
    if st.session_state.get("use_mock_fallback"):
        return handle_local_post(endpoint, payload)

    headers = {"Authorization": f"Bearer {st.session_state['access_token']}"}
    try:
        res = requests.post(f"{API_BASE_URL}{endpoint}", json=payload, headers=headers, timeout=5)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        print(f"API POST {endpoint} failed: {e}")
    return None


# ─────────────────────────────────────────────────────────────
# 🛡️ 인메모리 Mock 라우팅 에뮬레이터 (Spring Boot API Mocking)
# ─────────────────────────────────────────────────────────────

def handle_local_get(endpoint: str):
    """스프링 백엔드 API의 시그니처와 동일한 데이터를 인메모리 MOCK_DATABASE를 통해 즉각 반환합니다. (SQLite 의존성 완전 제거)"""
    try:
        # 1. 대시보드 요약 정보 집계
        if endpoint == "/api/dashboard/summary":
            regions_count = len(MOCK_DATABASE["regions"])
            total_stock = sum(item["quantity"] for item in MOCK_DATABASE["region_inventory"] if item["date"] == "2026-05-21")
            stockouts = len(MOCK_DATABASE["stock_out_logs"])
            return {
                "totalRegions": regions_count,
                "totalStock": total_stock,
                "totalStockOutIncidents": stockouts,
                "systemStatus": "STABLE (LOCAL MOCK)"
            }
            
        # 2. 최근 7일 재고 변동 트렌드
        elif endpoint == "/api/dashboard/stock-trend":
            # 일자별로 합산
            date_map = {}
            for item in MOCK_DATABASE["region_inventory"]:
                d = item["date"]
                qty = item["quantity"]
                date_map[d] = date_map.get(d, 0.0) + qty
                
            sorted_dates = sorted(date_map.keys())[-7:]
            return [{"date": d, "quantity": date_map[d]} for d in sorted_dates]
            
        # 3. 지점 목록 조회
        elif endpoint == "/api/regions":
            return MOCK_DATABASE["regions"]
            
        # 4. 특정 지점 재고 조회
        elif endpoint.startswith("/api/dashboard/region/") and endpoint.endswith("/inventory"):
            parts = endpoint.split("/")
            region_code = parts[4]
            rows = [item for item in MOCK_DATABASE["region_inventory"] if item["region_code"] == region_code]
            rows_sorted = sorted(rows, key=lambda x: x["date"], reverse=True)
            return [{
                "id": {
                    "productName": r["product_name"],
                    "date": r["date"]
                },
                "quantity": r["quantity"]
            } for r in rows_sorted]
            
        # 5. 특정 지점 날씨 조회
        elif endpoint.startswith("/api/dashboard/region/") and endpoint.endswith("/weather"):
            parts = endpoint.split("/")
            region_code = parts[4]
            rows = [item for item in MOCK_DATABASE["weather_cache"] if item["region_code"] == region_code]
            rows_sorted = sorted(rows, key=lambda x: x["date"], reverse=True)
            return [{
                "date": r["date"],
                "temp": r["temp"],
                "humidity": r["humidity"],
                "precipitation": r["precipitation"],
                "weatherDesc": r["weather_desc"]
            } for r in rows_sorted]
            
        # 6. 특정 지점 데이터 무결성 검증
        elif endpoint.startswith("/api/dashboard/region/") and "/integrity" in endpoint:
            return {
                "isConsistent": True,
                "message": "로컬 인메모리 데이터 정합성 검증 완료 (일치율 100%)"
            }
            
        # 7. 특정 지점 리스크 분석 스코어
        elif endpoint.startswith("/api/dashboard/region/") and endpoint.endswith("/risk-score"):
            parts = endpoint.split("/")
            region_code = parts[4]
            
            # 날씨 데이터 찾기
            w_rows = [item for item in MOCK_DATABASE["weather_cache"] if item["region_code"] == region_code]
            w_row = w_rows[0] if w_rows else None
            
            precip = w_row["precipitation"] if w_row and w_row.get("precipitation") else 0.0
            desc = w_row["weather_desc"] if w_row and w_row.get("weather_desc") else "정상"
            
            risk_score = min(100.0, 10.0 + (precip * 4.5))
            risk_level = "HIGH" if risk_score > 40.0 else "LOW"
            
            status_desc = f"현재 기상 상태: {desc} (강수량: {precip:.1f}mm). 리드타임 지연 리스크 보통."
            if risk_level == "HIGH":
                status_desc = f"⚠️ 기상이변 경보 발생! 강수량 {precip:.1f}mm 관측됨. 물류 경로 운송 지연 가능성 높음."
                
            # 최신 action_plan_msg 조회
            ins_rows = [item for item in MOCK_DATABASE["regional_insights"] if item["region_code"] == region_code]
            ins_row = ins_rows[0] if ins_rows else None
            action_plan = ins_row["action_plan_msg"] if ins_row else None
            
            return {
                "riskLevel": risk_level,
                "riskScore": risk_score,
                "description": status_desc,
                "actionPlan": action_plan
            }
            
        # 8. 대기 중인 발주 목록 조회
        elif endpoint == "/api/dashboard/pending-orders":
            pending = [item for item in MOCK_DATABASE["purchase_orders"] if item["status"] == "PENDING"]
            return [{
                "id": r["id"],
                "regionCode": r["region_code"],
                "productName": r["product_name"],
                "quantity": r["quantity"],
                "status": r["status"],
                "rejectionReason": r["rejection_reason"],
                "createdAt": r.get("createdAt")
            } for r in pending]

        # 9. 품목 금융 마스터 테이블 조회
        elif endpoint == "/api/dashboard/financials":
            return [{
                "productName": r["product_name"],
                "unitPrice": r["unit_price"],
                "holdingCostPerDay": r["holding_cost_per_day"]
            } for r in MOCK_DATABASE["product_financial_master"]]

        # 10. IoT 센서 및 기기 건강 요약 조회
        elif endpoint == "/api/iot/health-summary":
            return {
                "sensorActiveRate": 99.2,
                "temperatureStatus": "NORMAL",
                "humidityStatus": "NORMAL",
                "gpsSyncRate": 100.0,
                "connectionStatus": "STABLE",
                "lastActiveTime": "REALTIME"
            }
            
        return None
    except Exception as e:
        print(f"Local Emulation GET Error: {e}")
        return None

def handle_local_post(endpoint: str, payload: dict):
    """로컬 모드에서의 데이터 추가/수정을 인메모리 MOCK_DATABASE에 즉시 반영합니다. (SQLite 의존성 제거)"""
    try:
        # 1. 신규 지점 등록
        if endpoint == "/api/regions":
            name = payload.get("regionName")
            code = payload.get("regionCode")
            desc = payload.get("description")
            
            new_reg = {
                "regionName": name,
                "regionCode": code,
                "description": desc
            }
            MOCK_DATABASE["regions"].append(new_reg)
            return new_reg
            
        # 2. 발주 승인 처리
        elif endpoint.startswith("/api/dashboard/orders/") and endpoint.endswith("/approve"):
            parts = endpoint.split("/")
            order_id = int(parts[4])
            
            for item in MOCK_DATABASE["purchase_orders"]:
                if item["id"] == order_id:
                    item["status"] = "APPROVED"
                    break
            return {"status": "SUCCESS", "orderId": order_id}
            
        # 3. 발주 반려 처리 및 피드백 로그 적재
        elif endpoint.startswith("/api/dashboard/orders/") and endpoint.endswith("/reject"):
            parts = endpoint.split("/")
            order_id = int(parts[4])
            reason = payload.get("reason", "반려 사유 미지정")
            
            sku = "종합 품목"
            for item in MOCK_DATABASE["purchase_orders"]:
                if item["id"] == order_id:
                    item["status"] = "REJECTED"
                    item["rejection_reason"] = reason
                    sku = item["product_name"]
                    break
            
            # 피드백 로그 추가
            MOCK_DATABASE["order_feedback_log"].append({
                "order_id": order_id,
                "sku": sku,
                "action": "REJECTED",
                "reason": reason,
                "applied": 0
            })
            return {"status": "SUCCESS", "orderId": order_id}
            
        return None
    except Exception as e:
        print(f"Local Emulation POST Error: {e}")
        return None
