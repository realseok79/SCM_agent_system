# tests/test_rollback_engine.py
import pytest
import os
import db
from utils.parser.rollback_engine import rollback_batch
from utils.parser.exceptions import ConflictError

TEST_ROLLBACK_DB_PATH = "data/test_rollback_engine.db"

@pytest.fixture(autouse=True)
def setup_rollback_db(monkeypatch):
    monkeypatch.setattr("db.DB_PATH", TEST_ROLLBACK_DB_PATH)
    for suffix in ["", "-wal", "-shm"]:
        path = TEST_ROLLBACK_DB_PATH + suffix
        if os.path.exists(path):
            try:
                os.remove(path)
            except PermissionError:
                pass
    
    db.init_db()
    
    conn = db.get_db_connection()
    conn.execute("INSERT OR IGNORE INTO regions (region_name, region_code) VALUES ('Seoul', 'KR-11')")
    conn.commit()
    conn.close()
    
    yield
    
    for suffix in ["", "-wal", "-shm"]:
        path = TEST_ROLLBACK_DB_PATH + suffix
        if os.path.exists(path):
            try:
                os.remove(path)
            except PermissionError:
                pass

def test_rollback_batch_success():
    """APPROVED 배치를 REVOKING → REVIEW_REQUIRED로 정상 롤백"""
    conn = db.get_db_connection()
    
    # Seed an APPROVED batch with inventory rows
    conn.execute(
        """INSERT INTO import_batches (batch_id, company_id, file_name, file_sha256, status, version)
        VALUES ('RB_001', 'COMP_A', 'test.xlsx', 'hash_rb001', 'APPROVED', 3)"""
    )
    conn.execute(
        """INSERT INTO region_inventory (region_code, product_name, date, quantity, source_batch_id)
        VALUES ('KR-11', 'Mask', '2026-05-19', 100.0, 'RB_001')"""
    )
    conn.execute(
        """INSERT INTO region_inventory (region_code, product_name, date, quantity, source_batch_id)
        VALUES ('KR-11', 'Sanitizer', '2026-05-19', 50.0, 'RB_001')"""
    )
    conn.commit()
    
    # Execute rollback
    final_version = rollback_batch(conn, "RB_001", current_version=3, changed_by="ADMIN")
    
    # Verify batch status is now REVIEW_REQUIRED
    cursor = conn.cursor()
    cursor.execute("SELECT status, version FROM import_batches WHERE batch_id = 'RB_001'")
    row = cursor.fetchone()
    assert row["status"] == "REVIEW_REQUIRED"
    assert row["version"] == final_version
    
    # Verify physical inventory rows are deleted
    cursor.execute("SELECT COUNT(*) FROM region_inventory WHERE source_batch_id = 'RB_001'")
    count = cursor.fetchone()[0]
    assert count == 0
    
    # Verify audit history contains both transitions
    cursor.execute("SELECT from_status, to_status FROM batch_status_history WHERE batch_id = 'RB_001' ORDER BY rowid")
    history = cursor.fetchall()
    assert len(history) == 2
    assert history[0]["from_status"] == "APPROVED"
    assert history[0]["to_status"] == "REVOKING"
    assert history[1]["from_status"] == "REVOKING"
    assert history[1]["to_status"] == "REVIEW_REQUIRED"
    
    conn.close()

def test_rollback_batch_wrong_status():
    """APPROVED가 아닌 배치에 대해 롤백 시도 시 ConflictError"""
    conn = db.get_db_connection()
    
    conn.execute(
        """INSERT INTO import_batches (batch_id, company_id, file_name, file_sha256, status, version)
        VALUES ('RB_002', 'COMP_A', 'test.xlsx', 'hash_rb002', 'PARSED', 1)"""
    )
    conn.commit()
    
    with pytest.raises(ConflictError) as exc:
        rollback_batch(conn, "RB_002", current_version=1)
    assert "APPROVED" in str(exc.value)
    
    conn.close()

def test_rollback_batch_version_mismatch():
    """버전 불일치 시 ConflictError"""
    conn = db.get_db_connection()
    
    conn.execute(
        """INSERT INTO import_batches (batch_id, company_id, file_name, file_sha256, status, version)
        VALUES ('RB_003', 'COMP_A', 'test.xlsx', 'hash_rb003', 'APPROVED', 5)"""
    )
    conn.commit()
    
    with pytest.raises(ConflictError) as exc:
        rollback_batch(conn, "RB_003", current_version=3)
    assert "Version mismatch" in str(exc.value)
    
    conn.close()

def test_rollback_batch_not_found():
    """존재하지 않는 배치 ID에 대해 ConflictError"""
    conn = db.get_db_connection()
    
    with pytest.raises(ConflictError) as exc:
        rollback_batch(conn, "NONEXISTENT_BATCH", current_version=1)
    assert "not found" in str(exc.value)
    
    conn.close()
