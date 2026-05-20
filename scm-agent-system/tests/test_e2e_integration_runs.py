# tests/test_e2e_integration_runs.py
import pytest
import sqlite3
import pandas as pd
import os
from utils.parser.core import ingest_spreadsheet, BatchStatus, transition_batch_status

@pytest.fixture
def clean_db():
    """인메모리 SQLite DB 생성 및 스키마 초기화"""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. import_batches 테이블
    cursor.execute("""
        CREATE TABLE import_batches (
            batch_id TEXT PRIMARY KEY,
            company_id TEXT,
            file_name TEXT,
            file_sha256 TEXT,
            status TEXT,
            version INTEGER,
            drift_score REAL,
            quality_score REAL,
            validated_payload_snapshot BLOB,
            snapshot_checksum TEXT,
            parsed_at TEXT,
            reviewed_at TEXT,
            committed_at TEXT,
            failed_at TEXT,
            updated_at TEXT
        )
    """)
    
    # 2. batch_status_history 테이블
    cursor.execute("""
        CREATE TABLE batch_status_history (
            batch_id TEXT,
            from_status TEXT,
            to_status TEXT,
            changed_by TEXT,
            reason TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 3. staging_inventory_imports 테이블
    cursor.execute("""
        CREATE TABLE staging_inventory_imports (
            import_batch_id TEXT,
            company_id TEXT,
            region_code TEXT,
            product_name TEXT,
            date TEXT,
            quantity REAL,
            validation_status TEXT,
            source_row_index INTEGER
        )
    """)
    
    # 4. excel_parse_logs 테이블
    cursor.execute("""
        CREATE TABLE excel_parse_logs (
            import_batch_id TEXT,
            company_id TEXT,
            severity TEXT,
            message TEXT,
            column_name TEXT,
            row_index INTEGER
        )
    """)
    
    # 5. company_excel_mapping (시맨틱 맵퍼용)
    cursor.execute("""
        CREATE TABLE company_excel_mapping (
            company_id TEXT,
            raw_header TEXT,
            mapped_column TEXT,
            negative_score REAL
        )
    """)
    
    # 6. region_inventory 테이블
    cursor.execute("""
        CREATE TABLE region_inventory (
            region_code TEXT,
            product_name TEXT,
            date TEXT,
            quantity REAL,
            source_batch_id TEXT,
            PRIMARY KEY (region_code, product_name, date)
        )
    """)
    
    # 맵퍼 시딩
    cursor.execute("INSERT INTO company_excel_mapping VALUES ('COMP-E2E', 'region_code', 'region_code', 0.0)")
    cursor.execute("INSERT INTO company_excel_mapping VALUES ('COMP-E2E', 'product_name', 'product_name', 0.0)")
    cursor.execute("INSERT INTO company_excel_mapping VALUES ('COMP-E2E', 'date', 'date', 0.0)")
    cursor.execute("INSERT INTO company_excel_mapping VALUES ('COMP-E2E', 'quantity', 'quantity', 0.0)")
    
    conn.commit()
    return conn

def run_single_e2e_flow(db_conn, file_path, run_id):
    """
    1회 E2E 흐름 수행:
    CSV 업로드 -> AUTO-APPROVED 상태 검증 -> COMMITTED 상태 전환 -> 실재고(region_inventory)에 반영 확인
    """
    # 1. Excel/CSV 업로드 및 파싱 실행 (Drift < 0.2, Error/Critical = 0 이므로 AUTO-APPROVED 유도)
    batch_id, status = ingest_spreadsheet(db_conn, file_path, "COMP-E2E", f"run_{run_id}.csv")
    
    assert status == BatchStatus.APPROVED, f"E2E Run {run_id} failed to get AUTO-APPROVED"
    
    # DB에서 현재 버전 가져오기
    cursor = db_conn.cursor()
    cursor.execute("SELECT version FROM import_batches WHERE batch_id = ?", (batch_id,))
    row = cursor.fetchone()
    assert row is not None
    current_version = row["version"]
    
    # 2. APPROVED -> COMMITTED 상태 전이
    next_ver = transition_batch_status(
        db_conn,
        batch_id,
        BatchStatus.COMMITTED,
        current_version,
        BatchStatus.APPROVED,
        changed_by="admin",
        reason=f"E2E run {run_id} manual commit"
    )
    assert next_ver > current_version
    
    # 3. COMMITTED 이후, staging에서 region_inventory로 데이터 이관 (Auto-commit/Manual-commit 연동 시나리오 모사)
    db_conn.execute("BEGIN IMMEDIATE")
    cursor.execute("""
        SELECT region_code, product_name, date, quantity
        FROM staging_inventory_imports
        WHERE import_batch_id = ? AND validation_status = 'VALID'
    """, (batch_id,))
    staging_rows = cursor.fetchall()
    
    for sr in staging_rows:
        cursor.execute("""
            INSERT OR REPLACE INTO region_inventory (region_code, product_name, date, quantity, source_batch_id)
            VALUES (?, ?, ?, ?, ?)
        """, (sr["region_code"], sr["product_name"], sr["date"], sr["quantity"], batch_id))
    db_conn.commit()
    
    # 4. 실재고 반영 검증
    cursor.execute("""
        SELECT SUM(quantity) as total_qty FROM region_inventory WHERE source_batch_id = ?
    """, (batch_id,))
    res = cursor.fetchone()
    assert res["total_qty"] == 150.0, f"Inventory was not correctly reflected for batch {batch_id}"
    
    return True

def test_e2e_integration_three_consecutive_runs(tmp_path, clean_db):
    """
    [E2E 통합 테스트 검증 - 3회 연속 통과 보장]
    엑셀 업로드 → COMMITTED 상태 전환 → E2E 대시보드 수치 반영(재고 이동)까지의 시나리오를
    3회 연속으로 에러 없이 100% 성공률로 수행하는 검증 절차.
    """
    for i in range(1, 4):
        # 각 런마다 고유한 CSV 임시 파일 생성
        csv_file = tmp_path / f"run_{i}.csv"
        df = pd.DataFrame([
            {
                "region_code": f"KR-E2E-{i}",
                "product_name": "Part_X",
                "date": "2026-05-20",
                "quantity": 150.0,
                "company_id": "COMP-E2E",
                "warehouse_code": "WH-E2E"
            }
        ])
        df.to_csv(csv_file, index=False)
        
        # E2E 실행 및 검증
        success = run_single_e2e_flow(clean_db, str(csv_file), i)
        assert success is True, f"E2E Integration Run {i} failed!"
        
    print("\n[E2E VALIDATION SUCCESS] 3 consecutive runs completed with 0% error rate!")
