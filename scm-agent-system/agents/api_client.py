# agents/api_client.py
import requests
import time
from agents.config import NETWORK

API_BASE_URL = NETWORK.get("MOCK_API_HOST", "http://localhost:8080")

class SCMBackendClient:
    def __init__(self, username="admin", password="password"):
        self.username = username
        self.password = password
        self.access_token = None
        self.expires_at = 0

    def _login(self):
        try:
            url = f"{API_BASE_URL}/api/auth/login"
            res = requests.post(url, json={
                "username": self.username,
                "password": self.password
            }, timeout=5)
            if res.status_code == 200:
                data = res.json()
                self.access_token = data["accessToken"]
                # Expires in 15 minutes, let's refresh slightly early
                self.expires_at = time.time() + 900 - 30
                return True
        except Exception as e:
            print(f"SCMBackendClient login failed: {e}")
        return False

    def get_headers(self):
        if not self.access_token or time.time() >= self.expires_at:
            self._login()
        if self.access_token:
            return {"Authorization": f"Bearer {self.access_token}"}
        return {}

    def get(self, endpoint, params=None):
        headers = self.get_headers()
        try:
            res = requests.get(f"{API_BASE_URL}{endpoint}", headers=headers, params=params, timeout=10)
            if res.status_code == 200:
                return res.json()
            elif res.status_code in [401, 403]:
                # Retry once after logging in again
                self._login()
                headers = self.get_headers()
                res = requests.get(f"{API_BASE_URL}{endpoint}", headers=headers, params=params, timeout=10)
                if res.status_code == 200:
                    return res.json()
        except Exception as e:
            print(f"SCMBackendClient GET {endpoint} failed: {e}")
        return None

    def post(self, endpoint, json_data):
        headers = self.get_headers()
        try:
            res = requests.post(f"{API_BASE_URL}{endpoint}", headers=headers, json=json_data, timeout=10)
            if res.status_code == 200:
                return res.json()
            elif res.status_code in [401, 403]:
                self._login()
                headers = self.get_headers()
                res = requests.post(f"{API_BASE_URL}{endpoint}", headers=headers, json=json_data, timeout=10)
                if res.status_code == 200:
                    return res.json()
        except Exception as e:
            print(f"SCMBackendClient POST {endpoint} failed: {e}")
        return None

# Singleton client instance
client = SCMBackendClient()
