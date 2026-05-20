# tests/test_state_manager.py
import pytest
import os
import json
from utils.state_manager import load_lkv, save_lkv, STATE_FILE

@pytest.fixture(autouse=True)
def clean_state_file():
    """테스트 전후로 상태 파일을 정리"""
    backup = None
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            backup = f.read()
    
    yield
    
    # 복원
    if backup is not None:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            f.write(backup)
    elif os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)

def test_load_lkv_file_not_exists(tmp_path, monkeypatch):
    """파일이 없을 때 빈 딕셔너리 반환"""
    monkeypatch.setattr("utils.state_manager.STATE_FILE", str(tmp_path / "nonexistent.json"))
    result = load_lkv()
    assert result == {}

def test_load_lkv_valid_file(tmp_path, monkeypatch):
    """정상 JSON 파일 로드"""
    test_file = tmp_path / "test_lkv.json"
    data = {"South Korea": {"weather": "sunny"}}
    test_file.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr("utils.state_manager.STATE_FILE", str(test_file))
    
    result = load_lkv()
    assert result == data

def test_load_lkv_corrupted_file(tmp_path, monkeypatch):
    """손상된 JSON 파일 시 빈 딕셔너리 반환"""
    test_file = tmp_path / "corrupted.json"
    test_file.write_text("{invalid json!!!}", encoding="utf-8")
    monkeypatch.setattr("utils.state_manager.STATE_FILE", str(test_file))
    
    result = load_lkv()
    assert result == {}

def test_save_lkv_success(tmp_path, monkeypatch):
    """정상 저장 및 원자적 rename 검증"""
    test_file = str(tmp_path / "test_save.json")
    monkeypatch.setattr("utils.state_manager.STATE_FILE", test_file)
    
    data = {"Japan": {"macro": {"oil": 1.5}}}
    save_lkv(data)
    
    assert os.path.exists(test_file)
    with open(test_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded == data
    # tmp 파일이 남아있으면 안 됨
    assert not os.path.exists(test_file + ".tmp")

def test_save_lkv_creates_directory(tmp_path, monkeypatch):
    """디렉토리가 없으면 자동 생성"""
    test_file = str(tmp_path / "subdir" / "nested" / "state.json")
    monkeypatch.setattr("utils.state_manager.STATE_FILE", test_file)
    
    save_lkv({"test": True})
    assert os.path.exists(test_file)
