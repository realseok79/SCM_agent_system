# tests/test_recovery_scanner.py
import pytest
import sqlite3
import os
import db

TEST_RECOVERY_DB_PATH = "data/test_recovery_scanner.db"

@pytest.fixture(autouse=True)
def setup_recovery_db(monkeypatch):
    monkeypatch.setattr("db.DB_PATH", TEST_RECOVERY_DB_PATH)
    if os.path.exists(TEST_RECOVERY_DB_PATH):
        try:
            os.remove(TEST_RECOVERY_DB_PATH)
            if os.path.exists(TEST_RECOVERY_DB_PATH + "-wal"):
                os.remove(TEST_RECOVERY_DB_PATH + "-wal")
            if os.path.exists(TEST_RECOVERY_DB_PATH + "-shm"):
                os.remove(TEST_RECOVERY_DB_PATH + "-shm")
        except PermissionError:
            pass
            
    db.init_db()
    
    # Pre-seed regions
    conn = db.get_db_connection()
    conn.execute("INSERT OR IGNORE INTO regions (region_name, region_code) VALUES ('Seoul', 'KR-11')")
    conn.commit()
    conn.close()
    
    yield
    
    if os.path.exists(TEST_RECOVERY_DB_PATH):
        try:
            os.remove(TEST_RECOVERY_DB_PATH)
            if os.path.exists(TEST_RECOVERY_DB_PATH + "-wal"):
                os.remove(TEST_RECOVERY_DB_PATH + "-wal")
            if os.path.exists(TEST_RECOVERY_DB_PATH + "-shm"):
                os.remove(TEST_RECOVERY_DB_PATH + "-shm")
        except PermissionError:
            pass

def test_recovery_scanner_approved_batch():
    """Verify that APPROVED batches are auto-committed to region_inventory on startup"""
    conn = db.get_db_connection()
    cursor = conn.cursor()
    
    # 1. Seed import_batches with APPROVED status
    cursor.execute(
        """
        INSERT INTO import_batches (batch_id, company_id, file_name, file_sha256, status, version)
        VALUES ('BATCH_APP_123', 'COMP_A', 'test.xlsx', 'hash123', 'APPROVED', 1)
        """
    )
    # 2. Seed staging imports with VALID and INVALID row
    cursor.execute(
        """
        INSERT INTO staging_inventory_imports (import_batch_id, company_id, region_code, product_name, date, quantity, validation_status, source_row_index)
        VALUES ('BATCH_APP_123', 'COMP_A', 'KR-11', 'Mask', '2026-05-19', 100.0, 'VALID', 0)
        """
    )
    cursor.execute(
        """
        INSERT INTO staging_inventory_imports (import_batch_id, company_id, region_code, product_name, date, quantity, validation_status, source_row_index)
        VALUES ('BATCH_APP_123', 'COMP_A', 'KR-11', 'Sanitizer', '2026-05-19', -50.0, 'INVALID', 1)
        """
    )
    conn.commit()
    conn.close()
    
    # Run recovery scanner
    db.run_recovery_scanner()
    
    # Verify results
    conn = db.get_db_connection()
    cursor = conn.cursor()
    
    # Batch status should be COMMITTED and version incremented to 2
    cursor.execute("SELECT status, version FROM import_batches WHERE batch_id = 'BATCH_APP_123'")
    row = cursor.fetchone()
    assert row["status"] == "COMMITTED"
    assert row["version"] == 2
    
    # Only VALID staging row must be moved to physical region_inventory
    cursor.execute("SELECT region_code, product_name, quantity, source_batch_id FROM region_inventory")
    rows = cursor.fetchall()
    assert len(rows) == 1
    assert rows[0]["product_name"] == "Mask"
    assert rows[0]["quantity"] == 100.0
    assert rows[0]["source_batch_id"] == "BATCH_APP_123"
    
    # History must contain audit entry
    cursor.execute("SELECT from_status, to_status, changed_by FROM batch_status_history WHERE batch_id = 'BATCH_APP_123'")
    hist = cursor.fetchone()
    assert hist["from_status"] == "APPROVED"
    assert hist["to_status"] == "COMMITTED"
    assert hist["changed_by"] == "RECOVERY_SCANNER"
    
    conn.close()

def test_recovery_scanner_revoking_batch():
    """Verify that REVOKING batches are rolled back to REVIEW_REQUIRED on startup"""
    conn = db.get_db_connection()
    cursor = conn.cursor()
    
    # 1. Seed import_batches with REVOKING status
    cursor.execute(
        """
        INSERT INTO import_batches (batch_id, company_id, file_name, file_sha256, status, version)
        VALUES ('BATCH_REV_456', 'COMP_A', 'test.xlsx', 'hash456', 'REVOKING', 2)
        """
    )
    # 2. Seed region_inventory with rows belonging to this batch
    cursor.execute(
        """
        INSERT INTO region_inventory (region_code, product_name, date, quantity, source_batch_id)
        VALUES ('KR-11', 'Mask', '2026-05-19', 100.0, 'BATCH_REV_456')
        """
    )
    conn.commit()
    conn.close()
    
    # Run recovery scanner
    db.run_recovery_scanner()
    
    # Verify results
    conn = db.get_db_connection()
    cursor = conn.cursor()
    
    # Batch status should be REVIEW_REQUIRED and version incremented
    cursor.execute("SELECT status, version FROM import_batches WHERE batch_id = 'BATCH_REV_456'")
    row = cursor.fetchone()
    assert row["status"] == "REVIEW_REQUIRED"
    assert row["version"] == 3
    
    # Row from region_inventory must be completely deleted
    cursor.execute("SELECT COUNT(*) FROM region_inventory WHERE source_batch_id = 'BATCH_REV_456'")
    count = cursor.fetchone()[0]
    assert count == 0
    
    # History must contain audit entry
    cursor.execute("SELECT from_status, to_status, changed_by FROM batch_status_history WHERE batch_id = 'BATCH_REV_456'")
    hist = cursor.fetchone()
    assert hist["from_status"] == "REVOKING"
    assert hist["to_status"] == "REVIEW_REQUIRED"
    assert hist["changed_by"] == "RECOVERY_SCANNER"
    
    conn.close()
