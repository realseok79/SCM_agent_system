import os
import sqlite3
from agents.enterprise_data_agent import TeamSigmaDataAgent

def test_enterprise_data_agent_db_init(tmp_path):
    db_file = tmp_path / "test_enterprise.db"
    agent = TeamSigmaDataAgent(db_path=str(db_file))
    
    assert os.path.exists(db_file)
    with sqlite3.connect(str(db_file)) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        assert "sku_master" in tables
        assert "risk_trend_logs" in tables

def test_fetch_spire_maritime_data(monkeypatch):
    agent = TeamSigmaDataAgent(db_path=":memory:")
    
    class MockResponse:
        def __init__(self, status_code, text, json_data=None):
            self.status_code = status_code
            self.text = text
            self.json_data = json_data or {}
        def json(self):
            return self.json_data

    # Mock success call
    monkeypatch.setattr("requests.get", lambda url, headers, timeout: MockResponse(200, "OK", {"vessels": []}))
    res = agent.fetch_spire_maritime_data("fake_key")
    assert res == {"vessels": []}

    # Mock error call
    monkeypatch.setattr("requests.get", lambda url, headers, timeout: MockResponse(403, "Forbidden"))
    res = agent.fetch_spire_maritime_data("fake_key")
    assert res is None

    # Mock exception call
    def raise_err(*args, **kwargs):
        raise Exception("Network error")
    monkeypatch.setattr("requests.get", raise_err)
    res = agent.fetch_spire_maritime_data("fake_key")
    assert res is None
