# tests/test_tenant_cache_isolation.py
import pytest
import sqlite3
import os
import threading
import db
from utils.parser.semantic_mapper import resolve_semantic_mapping, canonicalize_header

TEST_TENANT_DB_PATH = "data/test_tenant_cache_isolation.db"

@pytest.fixture(autouse=True)
def setup_tenant_db(monkeypatch):
    monkeypatch.setattr("db.DB_PATH", TEST_TENANT_DB_PATH)
    if os.path.exists(TEST_TENANT_DB_PATH):
        try:
            os.remove(TEST_TENANT_DB_PATH)
            if os.path.exists(TEST_TENANT_DB_PATH + "-wal"):
                os.remove(TEST_TENANT_DB_PATH + "-wal")
            if os.path.exists(TEST_TENANT_DB_PATH + "-shm"):
                os.remove(TEST_TENANT_DB_PATH + "-shm")
        except PermissionError:
            pass
            
    db.init_db()
    
    yield
    
    if os.path.exists(TEST_TENANT_DB_PATH):
        try:
            os.remove(TEST_TENANT_DB_PATH)
            if os.path.exists(TEST_TENANT_DB_PATH + "-wal"):
                os.remove(TEST_TENANT_DB_PATH + "-wal")
            if os.path.exists(TEST_TENANT_DB_PATH + "-shm"):
                os.remove(TEST_TENANT_DB_PATH + "-shm")
        except PermissionError:
            pass

def test_tenant_negative_feedback_isolation():
    """Verify that user negative feedback mapping penalty is strictly isolated by company_id"""
    conn = db.get_db_connection()
    cursor = conn.cursor()
    
    # Raw header '지점' maps to standard 'region_code'
    # 1. Company A rejects '지점' mapping to 'region_code', giving a massive negative score of 10.0
    cursor.execute(
        """
        INSERT INTO company_excel_mapping (company_id, raw_header, mapped_column, confidence, negative_score)
        VALUES ('COMP_A', '지점', 'region_code', 0.85, 10.0)
        """
    )
    # 2. Company B has no rejection history for '지점' mapping to 'region_code'
    cursor.execute(
        """
        INSERT INTO company_excel_mapping (company_id, raw_header, mapped_column, confidence, negative_score)
        VALUES ('COMP_B', '지점', 'region_code', 0.85, 0.0)
        """
    )
    conn.commit()
    
    # 3. Resolve mapping for Company A -> must be heavily penalized or fail due to high negative score
    col_a, conf_a = resolve_semantic_mapping(conn, 'COMP_A', '지점')
    
    # 4. Resolve mapping for Company B -> must succeed with high confidence
    col_b, conf_b = resolve_semantic_mapping(conn, 'COMP_B', '지점')
    
    # Verification
    # Company A's confidence must be heavily degraded due to negative score penalty:
    # ConfidenceScore = 0.85 * max_sim * (1.0 - clamp(10.0 * 0.1, 0.0, 0.8))
    # Penalty factor is clamp(1.0, 0.0, 0.8) = 0.8, meaning 80% degradation!
    # Expected confidence for A is 0.85 * 1.0 * 0.2 = 0.17 (below threshold 0.40), returning (None, 0.0)
    assert col_a is None or conf_a < 0.3
    
    # Company B's mapping must be unaffected by Company A's penalty!
    assert col_b == 'region_code'
    assert conf_b == 0.85
    
    conn.close()

def test_concurrent_tenant_lookup_safety():
    """Verify that multiple concurrent threads resolving mappings for different tenants are isolated"""
    conn = db.get_db_connection()
    
    errors = []
    
    def worker_a():
        try:
            for _ in range(100):
                col, conf = resolve_semantic_mapping(conn, 'COMP_A', '지점')
                # Since COMP_A has penalty, should not be resolved or be lower
        except Exception as e:
            errors.append(e)
            
    def worker_b():
        try:
            for _ in range(100):
                col, conf = resolve_semantic_mapping(conn, 'COMP_B', '지점')
                if col != 'region_code':
                    errors.append(ValueError("Company B mapping corrupted by concurrent requests"))
        except Exception as e:
            errors.append(e)
            
    thread_a = threading.Thread(target=worker_a)
    thread_b = threading.Thread(target=worker_b)
    
    thread_a.start()
    thread_b.start()
    
    thread_a.join()
    thread_b.join()
    
    assert len(errors) == 0
    conn.close()
