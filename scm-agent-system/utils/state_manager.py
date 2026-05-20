import json
import os
import time

STATE_FILE = "data/last_known_values.json"

def load_lkv():
    """
    저장된 Last Known Values를 로드합니다.
    파일이 없거나 손상된 경우 기본 구조를 반환합니다.
    """
    if not os.path.exists(STATE_FILE):
        return {}
    
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"🚨 [LKV 로드 실패]: {e}")
        return {}

def save_lkv(data):
    """
    데이터를 원자적(Atomic)으로 저장하여 파일 손상을 방지합니다.
    """
    temp_file = STATE_FILE + ".tmp"
    try:
        # data 디렉토리가 없으면 생성
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # 덮어쓰기 (원자적 연산)
        os.rename(temp_file, STATE_FILE)
    except Exception as e:
        print(f"🚨 [LKV 저장 실패]: {e}")
        if os.path.exists(temp_file):
            os.remove(temp_file)
