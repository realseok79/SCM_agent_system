# tests/test_migration_dryrun.py
import pytest
import sqlite3
import os
import db

TEST_MIGRATION_DB_PATH = "data/test_migration_dryrun.db"

def test_migrations_dryrun():
    """Verify that all migrations apply forward-only in sequence and enforce constraints"""
    if os.path.exists(TEST_MIGRATION_DB_PATH):
        try:
            os.remove(TEST_MIGRATION_DB_PATH)
            if os.path.exists(TEST_MIGRATION_DB_PATH + "-wal"):
                os.remove(TEST_MIGRATION_DB_PATH + "-wal")
            if os.path.exists(TEST_MIGRATION_DB_PATH + "-shm"):
                os.remove(TEST_MIGRATION_DB_PATH + "-shm")
        except PermissionError:
            pass
            
    # Set DB path temporarily and execute init_db
    original_db_path = db.DB_PATH
    db.DB_PATH = TEST_MIGRATION_DB_PATH
    
    try:
        db.init_db()
        
        # Verify schema is populated correctly
        conn = db.get_db_connection()
        cursor = conn.cursor()
        
        # Verify schema_migrations table
        cursor.execute("SELECT version FROM schema_migrations ORDER BY version")
        versions = [r["version"] for r in cursor.fetchall()]
        assert "001" in versions
        assert "002" in versions
        assert "003" in versions
        assert "004" in versions
        
        # Verify table existence
        tables_query = "SELECT name FROM sqlite_master WHERE type='table'"
        cursor.execute(tables_query)
        tables = [r["name"] for r in cursor.fetchall()]
        
        assert "import_batches" in tables
        assert "staging_inventory_imports" in tables
        assert "excel_parse_logs" in tables
        assert "batch_status_history" in tables
        assert "company_excel_mapping" in tables
        assert "region_inventory" in tables
        
        # Verify CHECK constraints are registered on company_excel_mapping
        # Insert out of bounds confidence to verify constraint triggers IntegrityError
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute(
                """
                INSERT INTO company_excel_mapping (company_id, raw_header, mapped_column, confidence, negative_score)
                VALUES ('COMP_A', 'raw', 'region_code', 1.5, 0.0)
                """
            )
            
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute(
                """
                INSERT INTO company_excel_mapping (company_id, raw_header, mapped_column, confidence, negative_score)
                VALUES ('COMP_A', 'raw', 'region_code', 0.5, -1.0)
                """
            )
            
        conn.close()
        
    finally:
        db.DB_PATH = original_db_path
        if os.path.exists(TEST_MIGRATION_DB_PATH):
            try:
                os.remove(TEST_MIGRATION_DB_PATH)
                if os.path.exists(TEST_MIGRATION_DB_PATH + "-wal"):
                    os.remove(TEST_MIGRATION_DB_PATH + "-wal")
                if os.path.exists(TEST_MIGRATION_DB_PATH + "-shm"):
                    os.remove(TEST_MIGRATION_DB_PATH + "-shm")
            except PermissionError:
                pass
