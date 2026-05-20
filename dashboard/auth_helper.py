# dashboard/auth_helper.py
import requests
import streamlit as st
import time

API_BASE_URL = st.sidebar.text_input("Backend API URL", "http://localhost:8080")

def api_login(username, password):
    """
    POST /api/auth/login 엔드포인트를 호출하여 토큰을 발급받고 st.session_state에 기록합니다.
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
            st.session_state["token_expires_at"] = time.time() + 1800 # 30분
            return True, "Login successful"
        else:
            return False, f"Login failed: {res.text}"
    except Exception as e:
        return False, f"Connection failed: {e}"

def api_refresh():
    """
    POST /api/auth/refresh 엔드포인트를 사용하여 토큰 회전을 수행합니다.
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
            st.session_state["token_expires_at"] = time.time() + 1800
            return True
        else:
            # 토큰 탈취 등으로 무효화된 경우 로그아웃 처리
            api_logout()
            return False
    except Exception:
        return False

def api_logout():
    st.session_state.pop("access_token", None)
    st.session_state.pop("refresh_token", None)
    st.session_state.pop("user_role", None)
    st.session_state.pop("token_expires_at", None)

def check_auth_or_refresh():
    if "access_token" not in st.session_state:
        return False
    expires_at = st.session_state.get("token_expires_at", 0)
    if time.time() >= expires_at - 30: # 만료 30초 전 자동 갱신 시도
        return api_refresh()
    return True

def api_get(endpoint):
    """
    인증 헤더를 포함해 백엔드 API로부터 GET 요청을 보냅니다.
    """
    if not check_auth_or_refresh():
        return None
    headers = {"Authorization": f"Bearer {st.session_state['access_token']}"}
    try:
        res = requests.get(f"{API_BASE_URL}{endpoint}", headers=headers, timeout=10)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        print(f"API GET {endpoint} failed: {e}")
    return None

def api_post(endpoint, payload):
    """
    인증 헤더를 포함해 백엔드 API로부터 POST 요청을 보냅니다.
    """
    if not check_auth_or_refresh():
        return None
    headers = {"Authorization": f"Bearer {st.session_state['access_token']}"}
    try:
        res = requests.post(f"{API_BASE_URL}{endpoint}", json=payload, headers=headers, timeout=10)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        print(f"API POST {endpoint} failed: {e}")
    return None
