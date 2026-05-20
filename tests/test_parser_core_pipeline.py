# tests/test_parser_core_pipeline.py
import pytest
import os
import sqlite3
import pandas as pd
from utils.parser.core import ingest_spreadsheet, BatchStatus
from utils.parser.exceptions import FileTooLargeError

@pytest.fixture
def memory_db():
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
    
    # 맵퍼 시딩 추가
    cursor.execute("INSERT INTO company_excel_mapping VALUES ('COMP-A', 'region_code', 'region_code', 0.0)")
    cursor.execute("INSERT INTO company_excel_mapping VALUES ('COMP-A', 'product_name', 'product_name', 0.0)")
    cursor.execute("INSERT INTO company_excel_mapping VALUES ('COMP-A', 'date', 'date', 0.0)")
    cursor.execute("INSERT INTO company_excel_mapping VALUES ('COMP-A', 'quantity', 'quantity', 0.0)")
    
    conn.commit()
    return conn

def test_ingest_spreadsheet_file_too_large(tmp_path, memory_db):
    """50MB 초과 파일 예외 차단 검증"""
    large_file = tmp_path / "huge.csv"
    # 실제 디스크 크기를 속일 수 없으므로 1바이트만 쓰고 os.path.getsize를 Mocking
    large_file.write_text("dummy")
    
    import utils.parser.core
    # 51MB로 mock
    original_getsize = os.path.getsize
    os.path.getsize = lambda path: 55 * 1024 * 1024
    
    try:
        with pytest.raises(FileTooLargeError):
            ingest_spreadsheet(memory_db, str(large_file), "COMP-A", "huge.csv")
    finally:
        os.path.getsize = original_getsize

def test_ingest_spreadsheet_unsupported_format(tmp_path, memory_db):
    """지원되지 않는 확장자 에러 전이(FAILED) 검증"""
    bad_file = tmp_path / "data.txt"
    bad_file.write_text("unsupported")
    
    batch_id, status = ingest_spreadsheet(memory_db, str(bad_file), "COMP-A", "data.txt")
    assert status == BatchStatus.FAILED
    
    # DB 기록 상태 확인
    cursor = memory_db.cursor()
    cursor.execute("SELECT status FROM import_batches WHERE batch_id = ?", (batch_id,))
    assert cursor.fetchone()[0] == "FAILED"

def test_ingest_spreadsheet_golden_path_auto_approve(tmp_path, memory_db):
    """
    [Golden Path: Auto-approve Bypass]
    완벽한 스키마 정렬 및 검증 오류가 없는 정상 CSV 업로드 시 APPROVED 자동 바이패스 검증.
    """
    csv_file = tmp_path / "golden.csv"
    # region_code, product_name, date, quantity, company_id, warehouse_code 전체 정렬 데이터
    df = pd.DataFrame([
        {
            "region_code": "KR-11",
            "product_name": "Part_A",
            "date": "2026-05-20",
            "quantity": 150.0,
            "company_id": "COMP-A",
            "warehouse_code": "WH-SEOUL"
        }
    ])
    df.to_csv(csv_file, index=False)
    
    batch_id, status = ingest_spreadsheet(memory_db, str(csv_file), "COMP-A", "golden.csv")
    
    assert status == BatchStatus.APPROVED
    
    cursor = memory_db.cursor()
    cursor.execute("SELECT status, quality_score, drift_score FROM import_batches WHERE batch_id = ?", (batch_id,))
    row = cursor.fetchone()
    assert row["status"] == "APPROVED"
    assert row["quality_score"] == 1.0
    assert row["drift_score"] < 0.2

def test_ingest_spreadsheet_critical_validation_error(tmp_path, memory_db):
    """지점명이 완전 누락된 CRITICAL 에러가 감지되었을 때 FAILED로 자동 분류 및 중단 검증"""
    csv_file = tmp_path / "critical.csv"
    # region_code 가 비어있어 하드 에러 유발
    df = pd.DataFrame([
        {"region_code": "", "product_name": "Part_A", "date": "2026-05-20", "quantity": 150.0}
    ])
    df.to_csv(csv_file, index=False)
    
    batch_id, status = ingest_spreadsheet(memory_db, str(csv_file), "COMP-A", "critical.csv")
    assert status == BatchStatus.FAILED
    
    cursor = memory_db.cursor()
    cursor.execute("SELECT status FROM import_batches WHERE batch_id = ?", (batch_id,))
    assert cursor.fetchone()[0] == "FAILED"

def test_ingest_spreadsheet_warning_diverts_to_review(tmp_path, memory_db):
    """수량은 정상이나 음수 또는 Warning급 마일드한 오류가 있어 REVIEW_REQUIRED로 자동 분기 검증"""
    csv_file = tmp_path / "warning.csv"
    # quantity가 0인 경우 Warning 발생 유도 (validation_engine 규칙 상)
    df = pd.DataFrame([
        {"region_code": "KR-11", "product_name": "Part_A", "date": "2026-05-20", "quantity": 0.0}
    ])
    df.to_csv(csv_file, index=False)
    batch_id, status = ingest_spreadsheet(memory_db, str(csv_file), "COMP-A", "warning.csv")
    assert status == BatchStatus.REVIEW_REQUIRED
    
    cursor = memory_db.cursor()
    cursor.execute("SELECT status FROM import_batches WHERE batch_id = ?", (batch_id,))
    assert cursor.fetchone()[0] == "REVIEW_REQUIRED"

def test_ingest_spreadsheet_xlsx_format(tmp_path, memory_db):
    """Excel xlsx 확장자 형식 유입 시 정상적으로 read_excel로 분기하여 처리되는지 검증"""
    xlsx_file = tmp_path / "data.xlsx"
    df = pd.DataFrame([
        {
            "region_code": "KR-11",
            "product_name": "Part_A",
            "date": "2026-05-20",
            "quantity": 150.0,
            "company_id": "COMP-A",
            "warehouse_code": "WH-SEOUL"
        }
    ])
    # xlsx 파일 쓰기 (pandas openpyxl 엔진 이용)
    df.to_excel(xlsx_file, index=False)
    
    batch_id, status = ingest_spreadsheet(memory_db, str(xlsx_file), "COMP-A", "data.xlsx")
    assert status == BatchStatus.APPROVED

def test_ingest_spreadsheet_header_drift_crashed(tmp_path, memory_db):
    """지나친 스키마 Drift로 인해 HeaderDriftError 발생 시 CREATED -> FAILED 상태로 강하하는지 검증"""
    csv_file = tmp_path / "drift.csv"
    # 모르는 이상한 컬럼들로 도배하여 DriftScore > 0.5 유도
    df = pd.DataFrame([
        {"unknown_1": 1, "unknown_2": 2, "unknown_3": 3, "unknown_4": 4, "unknown_5": 5, "unknown_6": 6}
    ])
    df.to_csv(csv_file, index=False)
    
    batch_id, status = ingest_spreadsheet(memory_db, str(csv_file), "COMP-A", "drift.csv")
    assert status == BatchStatus.FAILED
    
    cursor = memory_db.cursor()
    cursor.execute("SELECT status FROM import_batches WHERE batch_id = ?", (batch_id,))
    assert cursor.fetchone()[0] == "FAILED"

def test_ingest_spreadsheet_validation_crashed(tmp_path, memory_db, monkeypatch):
    """검증 엔진(validate_rows) 오작동으로 예외 발생 시 FAILED 상태로 격리 전이 검증"""
    csv_file = tmp_path / "crash.csv"
    df = pd.DataFrame([
        {
            "region_code": "KR-11",
            "product_name": "Part_A",
            "date": "2026-05-20",
            "quantity": 150.0,
            "company_id": "COMP-A",
            "warehouse_code": "WH-SEOUL"
        }
    ])
    df.to_csv(csv_file, index=False)
    
    # validate_rows를 모킹하여 임의의 에러 유도
    import utils.parser.core
    monkeypatch.setattr(utils.parser.core, "validate_rows", lambda *args, **kwargs: exec("raise RuntimeError('Validation Engine Intercepted Crash')"))
    
    batch_id, status = ingest_spreadsheet(memory_db, str(csv_file), "COMP-A", "crash.csv")
    assert status == BatchStatus.FAILED
    
    cursor = memory_db.cursor()
    cursor.execute("SELECT status FROM import_batches WHERE batch_id = ?", (batch_id,))
    assert cursor.fetchone()[0] == "FAILED"
