# dashboard/auth_helper.py
import requests
import streamlit as st
import time
import os
import sqlite3

API_BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8080")

# [고도화 C12] 로컬 SQLite DB 백업 경로 및 파일 탐색
DASHBOARD_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.abspath(os.path.join(DASHBOARD_DIR, "../simulator/data/sigma_enterprise.db"))
if not os.path.exists(DB_PATH):
    DB_PATH = os.path.abspath(os.path.join(DASHBOARD_DIR, "../data/sigma_enterprise.db"))

def api_login(username, password):
    """
    POST /api/auth/login 엔드포인트를 호출하여 토큰을 발급받고 st.session_state 및 브라우저 쿠키에 기록합니다.
    """
    try:
        res = requests.post(f"{API_BASE_URL}/api/auth/login", json={
            "username": username,
            "password": password
        }, timeout=5)
        if res.status_code == 200:
            data = res.json()
            st.session_state["access_token"] = data["accessToken"]
            st.session_state["refresh_token"] = data["refreshToken"]
            st.session_state["user_role"] = data.get("role", "ROLE_USER")
            expires_at = time.time() + 1800 # 30분
            st.session_state["token_expires_at"] = expires_at
            st.session_state["is_offline"] = False
            
            # 마지막으로 성공한 인증 정보(Last Known Valid Session) 캐싱
            st.session_state["last_known_valid_session"] = {
                "access_token": data["accessToken"],
                "refresh_token": data["refreshToken"],
                "role": data.get("role", "ROLE_USER")
            }
            
            cookie_manager = st.session_state.get("cookie_manager")
            if cookie_manager:
                cookie_manager.set("access_token", data["accessToken"])
                cookie_manager.set("refresh_token", data["refreshToken"])
                cookie_manager.set("user_role", data.get("role", "ROLE_USER"))
                cookie_manager.set("token_expires_at", str(expires_at))
            return True, "Login successful"
        else:
            return False, f"Login failed: {res.text}"
    except Exception as e:
        # 연결 실패 시 만약 기존 세션이 있다면 오프라인 모드로 자동 전환
        if "last_known_valid_session" in st.session_state:
            st.session_state["is_offline"] = True
            session = st.session_state["last_known_valid_session"]
            st.session_state["access_token"] = session["access_token"]
            st.session_state["refresh_token"] = session["refresh_token"]
            st.session_state["user_role"] = session["role"]
            st.session_state["token_expires_at"] = time.time() + 1800
            return True, "Offline mode activated using cached credentials"
            
        # 만약 기존 세션이 없고 backend 연결에 실패했지만, 사용자 입력이 admin / admin 또는 demo / demo 이면 로컬 오프라인 접속 허용!
        if (username == "admin" and password == "admin") or (username == "demo" and password == "demo"):
            st.session_state["is_offline"] = True
            st.session_state["access_token"] = "offline-access-token"
            st.session_state["refresh_token"] = "offline-refresh-token"
            role = "ROLE_ADMIN" if username == "admin" else "ROLE_LOGISTICS"
            st.session_state["user_role"] = role
            st.session_state["token_expires_at"] = time.time() + 1800
            st.session_state["last_known_valid_session"] = {
                "access_token": "offline-access-token",
                "refresh_token": "offline-refresh-token",
                "role": role
            }
            return True, "Offline mode activated using fallback credentials"
        return False, f"Connection failed: {e}"

def api_refresh():
    """
    POST /api/auth/refresh 엔드포인트를 사용하여 토큰 회전을 수행하고 쿠키를 업데이트합니다.
    """
    if "refresh_token" not in st.session_state:
        return False
    try:
        res = requests.post(f"{API_BASE_URL}/api/auth/refresh", json={
            "refreshToken": st.session_state["refresh_token"]
        }, timeout=5)
        if res.status_code == 200:
            data = res.json()
            st.session_state["access_token"] = data["accessToken"]
            st.session_state["refresh_token"] = data["refreshToken"]
            expires_at = time.time() + 1800
            st.session_state["token_expires_at"] = expires_at
            st.session_state["is_offline"] = False
            
            # 캐시 업데이트
            st.session_state["last_known_valid_session"] = {
                "access_token": data["accessToken"],
                "refresh_token": data["refreshToken"],
                "role": st.session_state.get("user_role", "ROLE_USER")
            }
            
            cookie_manager = st.session_state.get("cookie_manager")
            if cookie_manager:
                cookie_manager.set("access_token", data["accessToken"])
                cookie_manager.set("refresh_token", data["refreshToken"])
                cookie_manager.set("token_expires_at", str(expires_at))
            return True
        else:
            # 토큰 탈취 등으로 무효화된 경우 로그아웃 처리
            api_logout()
            return False
    except Exception:
        # 오프라인 상태이면 그냥 마지막 인증 정보 연장
        if "last_known_valid_session" in st.session_state:
            st.session_state["is_offline"] = True
            st.session_state["token_expires_at"] = time.time() + 1800
            return True
        return False

def api_logout():
    st.session_state.pop("access_token", None)
    st.session_state.pop("refresh_token", None)
    st.session_state.pop("user_role", None)
    st.session_state.pop("token_expires_at", None)
    st.session_state.pop("is_offline", None)
    st.session_state.pop("last_known_valid_session", None)
    
    cookie_manager = st.session_state.get("cookie_manager")
    if cookie_manager:
        cookie_manager.delete("access_token")
        cookie_manager.delete("refresh_token")
        cookie_manager.delete("user_role")
        cookie_manager.delete("token_expires_at")

def check_auth_or_refresh():
    if "access_token" not in st.session_state:
        if "last_known_valid_session" in st.session_state:
            session = st.session_state["last_known_valid_session"]
            st.session_state["access_token"] = session["access_token"]
            st.session_state["refresh_token"] = session["refresh_token"]
            st.session_state["user_role"] = session["role"]
            st.session_state["token_expires_at"] = time.time() + 1800
            return True
        return False
    expires_at = st.session_state.get("token_expires_at", 0)
    if time.time() >= expires_at - 30: # 만료 30초 전 자동 갱신 시도
        return api_refresh()
    return True

@st.cache_data(ttl=60)
def api_get(endpoint):
    """
    인증 헤더를 포함해 백엔드 API로부터 GET 요청을 보냅니다.
    오프라인 상태 시 로컬 SQLite DB로 대체합니다.
    """
    is_offline = st.session_state.get("is_offline", False)
    if not is_offline:
        if not check_auth_or_refresh():
            return None
        headers = {"Authorization": f"Bearer {st.session_state['access_token']}"}
        try:
            res = requests.get(f"{API_BASE_URL}{endpoint}", headers=headers, timeout=5)
            if res.status_code == 200:
                return res.json()
            elif res.status_code == 401:
                api_logout()
                st.rerun()
        except Exception as e:
            print(f"API GET {endpoint} failed: {e}. Switching to offline fallback.")
            st.session_state["is_offline"] = True
            
    # 로컬 SQLite DB에서 데이터 수집하는 Fallback 실행
    return query_local_sqlite_fallback(endpoint)

def api_post(endpoint, payload):
    """
    인증 헤더를 포함해 백엔드 API로부터 POST 요청을 보냅니다.
    오프라인 상태 시 차단 경고를 표출합니다.
    """
    if st.session_state.get("is_offline", False):
        st.error("⚠️ 시스템이 오프라인 모드입니다. 쓰기(Mutation) 작업이 차단되었습니다.")
        return None
    if not check_auth_or_refresh():
        return None
    headers = {"Authorization": f"Bearer {st.session_state['access_token']}"}
    try:
        res = requests.post(f"{API_BASE_URL}{endpoint}", json=payload, headers=headers, timeout=5)
        if res.status_code == 200:
            st.cache_data.clear() # Mutating call: Clear cache!
            return res.json()
        elif res.status_code == 401:
            api_logout()
            st.rerun()
    except Exception as e:
        print(f"API POST {endpoint} failed: {e}")
        st.error("❌ 서버가 응답하지 않거나 오프라인 상태여서 요청을 수행할 수 없습니다.")
    return None

def api_delete(endpoint):
    """
    인증 헤더를 포함해 백엔드 API로부터 DELETE 요청을 보냅니다.
    오프라인 상태 시 차단 경고를 표출합니다.
    """
    if st.session_state.get("is_offline", False):
        st.error("⚠️ 시스템이 오프라인 모드입니다. 쓰기(Mutation) 작업이 차단되었습니다.")
        return False
    if not check_auth_or_refresh():
        return False
    headers = {"Authorization": f"Bearer {st.session_state['access_token']}"}
    try:
        res = requests.delete(f"{API_BASE_URL}{endpoint}", headers=headers, timeout=5)
        if res.status_code in [200, 204]:
            st.cache_data.clear() # Mutating call: Clear cache!
            return True
        elif res.status_code == 401:
            api_logout()
            st.rerun()
    except Exception as e:
        print(f"API DELETE {endpoint} failed: {e}")
        st.error("❌ 서버가 응답하지 않거나 오프라인 상태여서 요청을 수행할 수 없습니다.")
    return False

def api_patch(endpoint, payload):
    """
    인증 헤더를 포함해 백엔드 API로부터 PATCH 요청을 보냅니다.
    오프라인 상태 시 차단 경고를 표출합니다.
    """
    if st.session_state.get("is_offline", False):
        st.error("⚠️ 시스템이 오프라인 모드입니다. 쓰기(Mutation) 작업이 차단되었습니다.")
        return None
    if not check_auth_or_refresh():
        return None
    headers = {"Authorization": f"Bearer {st.session_state['access_token']}"}
    try:
        res = requests.patch(f"{API_BASE_URL}{endpoint}", json=payload, headers=headers, timeout=5)
        if res.status_code == 200:
            st.cache_data.clear() # Mutating call: Clear cache!
            return res.json()
        elif res.status_code == 401:
            api_logout()
            st.rerun()
    except Exception as e:
        print(f"API PATCH {endpoint} failed: {e}")
        st.error("❌ 서버가 응답하지 않거나 오프라인 상태여서 요청을 수행할 수 없습니다.")
    return None

def query_local_sqlite_fallback(endpoint):
    """
    백엔드 API 서버 오프라인 시 로컬 SQLite DB에서 데이터를 가져오는 예외 경로
    """
    def get_local_conn():
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    try:
        # endpoint가 /api/regions 인 경우
        if endpoint == "/api/regions":
            with get_local_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT region_name, region_code, description FROM regions")
                rows = cursor.fetchall()
                return [{"regionName": r["region_name"], "regionCode": r["region_code"], "description": r["description"]} for r in rows]

        # endpoint가 /api/iot/health-summary 인 경우
        elif endpoint == "/api/iot/health-summary":
            return {"averageHealthScore": 92.5, "status": "Offline Fallback"}

        # endpoint가 /api/iot/devices 인 경우
        elif endpoint == "/api/iot/devices":
            return [
                {"deviceId": "SENS-TEMP-001", "regionCode": "KR-11", "sensorType": "temperature", "status": "ACTIVE", "lastPingAt": "2026-05-26 12:00:00"},
                {"deviceId": "SENS-HUMID-001", "regionCode": "KR-11", "sensorType": "humidity", "status": "ACTIVE", "lastPingAt": "2026-05-26 12:00:00"},
                {"deviceId": "SENS-VIBR-002", "regionCode": "KR-26", "sensorType": "vibration", "status": "MAINTENANCE", "lastPingAt": "2026-05-25 18:30:00"},
                {"deviceId": "SENS-RFID-003", "regionCode": "KR-49", "sensorType": "rfid_count", "status": "ACTIVE", "lastPingAt": "2026-05-26 11:45:00"}
            ]

        # endpoint가 /api/audit-logs 인 경우
        elif endpoint == "/api/audit-logs":
            with get_local_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, event_type, action_details, user_id, created_at FROM system_audit_log ORDER BY created_at DESC")
                rows = cursor.fetchall()
                logs = []
                for r in rows:
                    logs.append({
                        "id": r["id"],
                        "eventType": r["event_type"],
                        "message": r["action_details"],
                        "triggeredBy": r["user_id"] or "SYSTEM_AGENT",
                        "recordedAt": r["created_at"]
                    })
                return logs

        # endpoint가 /api/dashboard/pending-orders 인 경우
        elif endpoint == "/api/dashboard/pending-orders":
            with get_local_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM inventory_rebalancing_orders WHERE status = 'PENDING'")
                rows = cursor.fetchall()
                orders = []
                for r in rows:
                    orders.append({
                        "transferId": r["transfer_id"],
                        "productName": r["product_name"],
                        "fromRegion": r["from_region"],
                        "toRegion": r["to_region"],
                        "transferQty": r["transfer_qty"],
                        "savedCost": r["saved_cost"],
                        "status": r["status"],
                        "createdAt": r["created_at"]
                    })
                return orders

        # endpoint가 /api/dashboard/summary 인 경우
        elif endpoint == "/api/dashboard/summary":
            with get_local_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM regions")
                total_regions = cursor.fetchone()[0]
                
                cursor.execute("SELECT SUM(quantity) FROM region_inventory")
                total_stock = cursor.fetchone()[0] or 0.0
                
                cursor.execute("SELECT COUNT(*) FROM stock_out_logs")
                total_incidents = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(DISTINCT product_name) FROM region_inventory")
                total_sku = cursor.fetchone()[0]
                
                cursor.execute("SELECT SUM(saved_cost) FROM inventory_rebalancing_orders")
                saved_cost = cursor.fetchone()[0] or 0.0
                
                return {
                    "totalRegions": total_regions,
                    "totalStock": total_stock,
                    "totalStockOutIncidents": total_incidents,
                    "totalSkuCount": total_sku if total_sku > 0 else 3,
                    "savedCostDelta": saved_cost,
                    "systemStatus": "STABLE (Offline Fallback)"
                }

        # endpoint가 /api/dashboard/stock-trend 인 경우
        elif endpoint == "/api/dashboard/stock-trend":
            with get_local_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT date, SUM(quantity) as quantity FROM region_inventory GROUP BY date ORDER BY date")
                rows = cursor.fetchall()
                return [{"date": r["date"], "quantity": r["quantity"]} for r in rows]

        # endpoint가 /api/dashboard/batch-inventories 인 경우
        elif endpoint == "/api/dashboard/batch-inventories":
            with get_local_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT region_code, SUM(quantity) as qty FROM region_inventory GROUP BY region_code")
                rows = cursor.fetchall()
                return {r["region_code"]: r["qty"] for r in rows}

        # endpoint가 /api/dashboard/batch-risks 인 경우
        elif endpoint == "/api/dashboard/batch-risks":
            with get_local_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT region_code, region_name FROM regions")
                regions_list = cursor.fetchall()
                
                result = {}
                for r in regions_list:
                    code = r["region_code"]
                    # check weather_cache for extreme weather
                    cursor.execute("SELECT temp, precipitation FROM weather_cache WHERE region_code = ?", (code,))
                    weather_rows = cursor.fetchall()
                    severe_weather = False
                    for w in weather_rows:
                        temp = w[0]
                        precip = w[1]
                        if (temp is not None and (temp > 38.0 or temp < -15.0)) or (precip is not None and precip > 50.0):
                            severe_weather = True
                            break
                    
                    score = 85.0 if severe_weather else 25.0
                    level = "HIGH" if score >= 60.0 else "LOW"
                    desc = "기상 악화 경보: 운송 지연이 감지되었습니다. (Offline Fallback)" if severe_weather else "정상 상태: 운송 지연 위험도가 낮습니다. (Offline Fallback)"
                    
                    # check latest insight
                    cursor.execute("SELECT action_plan_msg FROM regional_insights WHERE region_code = ? ORDER BY date DESC LIMIT 1", (code,))
                    insight_row = cursor.fetchone()
                    insight_msg = insight_row[0] if insight_row else "정상 운영 절차 진행 권고"
                    
                    result[code] = {
                        "risk": {
                            "regionCode": code,
                            "riskScore": score,
                            "riskLevel": level,
                            "description": desc
                        },
                        "insight": {
                            "regionCode": code,
                            "actionPlanMsg": insight_msg,
                            "source": "RULE_ENGINE"
                        }
                    }
                return result

        # /api/dashboard/rebalancing-orders
        elif endpoint == "/api/dashboard/rebalancing-orders":
            with get_local_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM inventory_rebalancing_orders")
                rows = cursor.fetchall()
                orders = []
                for r in rows:
                    orders.append({
                        "transferId": r["transfer_id"],
                        "productName": r["product_name"],
                        "fromRegion": r["from_region"],
                        "toRegion": r["to_region"],
                        "transferQty": r["transfer_qty"],
                        "savedCost": r["saved_cost"],
                        "status": r["status"],
                        "createdAt": r["created_at"]
                    })
                return orders

        # /api/dashboard/region/{code}/weather
        elif endpoint.startswith("/api/dashboard/region/") and endpoint.endswith("/weather"):
            parts = endpoint.split("/")
            code = parts[4]
            with get_local_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM weather_cache WHERE region_code = ?", (code,))
                rows = cursor.fetchall()
                return [{
                    "regionCode": r["region_code"],
                    "date": r["date"],
                    "temp": r["temp"],
                    "humidity": r["humidity"],
                    "precipitation": r["precipitation"],
                    "weatherDesc": r["weather_desc"]
                } for r in rows]

        # /api/dashboard/region/{code}/aging
        elif endpoint.startswith("/api/dashboard/region/") and endpoint.endswith("/aging"):
            parts = endpoint.split("/")
            code = parts[4]
            with get_local_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT product_name, date, quantity FROM region_inventory WHERE region_code = ? ORDER BY date", (code,))
                rows = cursor.fetchall()
                return [{
                    "productName": r["product_name"],
                    "date": r["date"],
                    "quantity": r["quantity"]
                } for r in rows]

        # /api/dashboard/region/{code}/inventory
        elif endpoint.startswith("/api/dashboard/region/") and endpoint.endswith("/inventory"):
            parts = endpoint.split("/")
            code = parts[4]
            with get_local_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT region_code, product_name, date, quantity FROM region_inventory WHERE region_code = ?", (code,))
                rows = cursor.fetchall()
                return [{
                    "id": {
                        "regionCode": r["region_code"],
                        "productName": r["product_name"],
                        "date": r["date"]
                    },
                    "quantity": r["quantity"]
                } for r in rows]

        # /api/dashboard/mlops-metrics
        elif endpoint == "/api/dashboard/mlops-metrics":
            return {
                "averageDriftScore": 2.45,
                "averageQualityScore": 98.7,
                "totalBatchesCount": 15,
                "simulatedLatency": 12.4,
                "simulatedThroughput": 5000,
                "activeWorkers": 4
            }

    except Exception as e:
        print(f"Error querying local sqlite fallback for {endpoint}: {e}")
    
    return None
