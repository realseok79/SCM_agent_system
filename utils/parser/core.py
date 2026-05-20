# utils/parser/core.py
import os
import time
import json
import hashlib
import pandas as pd
from enum import Enum
from typing import Tuple

from utils.parser.exceptions import (
    SAEIEError,
    NestedTransactionError,
    ConflictError,
    VersionOverflowError,
    InvalidStateTransitionError,
    HeaderDriftError,
    FileTooLargeError
)
from utils.parser.header_detector import detect_header_row, extract_clean_df
from utils.parser.semantic_mapper import resolve_semantic_mapping
from utils.parser.drift_engine import validate_drift
from utils.parser.validation_engine import validate_rows
from utils.parser.snapshot_utils import serialize_snapshot

class BatchStatus(Enum):
    CREATED = 'CREATED'
    PARSED = 'PARSED'
    APPROVED = 'APPROVED'
    REVIEW_REQUIRED = 'REVIEW_REQUIRED'
    COMMITTED = 'COMMITTED'
    REVOKING = 'REVOKING'
    FAILED = 'FAILED'
    ROLLED_BACK = 'ROLLED_BACK'

ALLOWED_TRANSITIONS = {
    BatchStatus.CREATED: {BatchStatus.PARSED, BatchStatus.FAILED},
    BatchStatus.PARSED: {BatchStatus.APPROVED, BatchStatus.REVIEW_REQUIRED, BatchStatus.FAILED},
    BatchStatus.REVIEW_REQUIRED: {BatchStatus.APPROVED, BatchStatus.FAILED, BatchStatus.ROLLED_BACK},
    BatchStatus.APPROVED: {BatchStatus.COMMITTED, BatchStatus.REVOKING},
    BatchStatus.REVOKING: {BatchStatus.REVIEW_REQUIRED, BatchStatus.FAILED},
    BatchStatus.COMMITTED: set(),
    BatchStatus.FAILED: set(),
    BatchStatus.ROLLED_BACK: set()
}

def is_transaction_active(db_conn) -> bool:
    """Check if connection is already inside active transaction"""
    return getattr(db_conn, "in_transaction", False)

def validate_transition(from_status: BatchStatus, to_status: BatchStatus) -> None:
    """Enforce state transition matrix invariants"""
    if from_status in {BatchStatus.COMMITTED, BatchStatus.FAILED, BatchStatus.ROLLED_BACK}:
        raise InvalidStateTransitionError(f"Terminal state '{from_status.value}' is immutable.")
    if to_status not in ALLOWED_TRANSITIONS.get(from_status, set()):
        raise InvalidStateTransitionError(f"Invalid transition path from '{from_status.value}' to '{to_status.value}'.")

def transition_batch_status(
    db_conn,
    batch_id: str,
    next_status: BatchStatus,
    current_version: int,
    expected_status: BatchStatus,
    changed_by: str = "SYSTEM",
    reason: str | None = None
) -> int:
    """
    Executes a transaction-protected status transition for a batch,
    performing optimistic concurrency lock checks.
    """
    if is_transaction_active(db_conn):
        raise NestedTransactionError("Cannot start status transition: connection is already inside active transaction.")
        
    cursor = db_conn.cursor()
    try:
        db_conn.execute("BEGIN IMMEDIATE")
        
        cursor.execute(
            "SELECT status, version FROM import_batches WHERE batch_id = ?",
            (batch_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise ConflictError(f"Batch {batch_id} not found.")
            
        db_status, db_version = row[0], row[1]
        
        if db_version != current_version:
            raise ConflictError(f"Version mismatch. Expected: {current_version}, DB: {db_version}")
            
        if db_status != expected_status.value:
            raise ConflictError(f"Status mismatch. Expected: {expected_status.value}, DB: {db_status}")
            
        validate_transition(BatchStatus(db_status), next_status)
        
        next_version = db_version + 1
        if next_version >= 9223372036854775807:
            raise VersionOverflowError("Optimistic lock version integer overflow detected.")
            
        cursor.execute(
            """
            UPDATE import_batches 
            SET status = ?, version = ?, 
                parsed_at = CASE WHEN ? = 'PARSED' THEN datetime('now') ELSE parsed_at END,
                reviewed_at = CASE WHEN ? = 'APPROVED' OR ? = 'REVIEW_REQUIRED' THEN datetime('now') ELSE reviewed_at END,
                committed_at = CASE WHEN ? = 'COMMITTED' THEN datetime('now') ELSE committed_at END,
                failed_at = CASE WHEN ? = 'FAILED' THEN datetime('now') ELSE failed_at END,
                updated_at = datetime('now')
            WHERE batch_id = ? AND version = ?
            """,
            (next_status.value, next_version, next_status.value, next_status.value, next_status.value, 
             next_status.value, next_status.value, batch_id, db_version)
        )
        
        cursor.execute(
            """
            INSERT INTO batch_status_history (batch_id, from_status, to_status, changed_by, reason)
            VALUES (?, ?, ?, ?, ?)
            """,
            (batch_id, db_status, next_status.value, changed_by, reason)
        )
        
        db_conn.commit()
        return next_version
        
    except Exception:
        if db_conn.in_transaction:
            db_conn.rollback()
        raise
    finally:
        cursor.close()

def calculate_file_sha256(file_path: str) -> str:
    """Streams file reading in 64KB chunks to calculate SHA256 safely"""
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            sha.update(chunk)
    return sha.hexdigest()

def ingest_spreadsheet(
    db_conn,
    file_path: str,
    company_id: str,
    file_name: str,
    changed_by: str = "SYSTEM"
) -> Tuple[str, BatchStatus]:
    """
    Main SAEIE pipeline Facade:
    1. Limit checks (50MB)
    2. File hashing (SHA256 stream)
    3. Initialize import_batch record in CREATED status
    4. Detect header row & extract clean DataFrame
    5. Resolve semantic mappings & compute DriftScore
    6. Perform row validations (Critical, Error, Warning classification)
    7. Process Auto-approve Bypass policy or divert to Review/Failed
    """
    # 1. Size guard
    if os.path.getsize(file_path) > 52428800:  # 50MB
        raise FileTooLargeError("File size exceeds maximum limit of 50MB.")
        
    # 2. File hash
    file_hash = calculate_file_sha256(file_path)
    
    # Generate unique UUID/hash-based batch ID
    batch_id = f"BATCH_{file_hash[:16]}_{int(time.time())}"
    
    # 3. Create CREATED batch record
    cursor = db_conn.cursor()
    db_conn.execute("BEGIN IMMEDIATE")
    cursor.execute(
        """
        INSERT INTO import_batches (batch_id, company_id, file_name, file_sha256, status, version)
        VALUES (?, ?, ?, ?, 'CREATED', 1)
        """,
        (batch_id, company_id, file_name, file_hash)
    )
    cursor.execute(
        """
        INSERT INTO batch_status_history (batch_id, from_status, to_status, changed_by, reason)
        VALUES (?, NULL, 'CREATED', ?, 'Batch ingestion initiated.')
        """,
        (batch_id, changed_by)
    )
    db_conn.commit()
    
    version = 1
    
    # Read file using pandas
    _, ext = os.path.splitext(file_name.lower())
    try:
        if ext in [".xlsx", ".xls"]:
            df = pd.read_excel(file_path)
        elif ext in [".csv"]:
            df = pd.read_csv(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")
    except Exception as e:
        # Move batch to FAILED
        transition_batch_status(
            db_conn, batch_id, BatchStatus.FAILED, version, BatchStatus.CREATED,
            changed_by, f"Failed to read file: {e}"
        )
        return batch_id, BatchStatus.FAILED
        
    # 4. Header Detection
    header_idx = detect_header_row(df)
    clean_df = extract_clean_df(df, header_idx)
    clean_df = clean_df.astype(object).where(pd.notnull(clean_df), None)
    
    # 5. Semantic Mapping
    mapping = {}
    mapped_cols_list = []
    unknown_cols_count = 0
    
    for raw_col in clean_df.columns:
        if raw_col.startswith("UNNAMED_COL_"):
            unknown_cols_count += 1
            mapped_cols_list.append(None)
            mapping[raw_col] = None
            continue
            
        std_col, _ = resolve_semantic_mapping(db_conn, company_id, raw_col)
        if std_col:
            mapped_cols_list.append(std_col)
            mapping[raw_col] = std_col
        else:
            unknown_cols_count += 1
            mapped_cols_list.append(None)
            mapping[raw_col] = None
            
    # 6. Drift validate
    try:
        drift_score = validate_drift(mapped_cols_list, unknown_cols_count)
    except HeaderDriftError as e:
        # CREATED -> FAILED direct transition (Minor #4)
        transition_batch_status(
            db_conn, batch_id, BatchStatus.FAILED, version, BatchStatus.CREATED,
            changed_by, str(e)
        )
        return batch_id, BatchStatus.FAILED
        
    # Move status from CREATED -> PARSED
    version = transition_batch_status(
        db_conn, batch_id, BatchStatus.PARSED, version, BatchStatus.CREATED,
        changed_by, f"Header mapping complete. DriftScore: {drift_score}"
    )
    
    # 7. Row Validation
    try:
        payload_list, has_critical, has_error, has_warning = validate_rows(clean_df, mapping, company_id)
    except Exception as e:
        transition_batch_status(
            db_conn, batch_id, BatchStatus.FAILED, version, BatchStatus.PARSED,
            changed_by, f"Row validation crashed: {e}"
        )
        return batch_id, BatchStatus.FAILED
        
    # Determine quality score: percentage of VALID rows (rows with no critical or error severity issues)
    valid_rows_count = sum(1 for p in payload_list if not any(e["severity"] in {"CRITICAL", "ERROR"} for e in p["validation_errors"]))
    quality_score = valid_rows_count / max(len(payload_list), 1)
    
    # Build compressed binary payload snapshot & SHA256 checksum
    snapshot_blob = serialize_snapshot(payload_list)
    snapshot_checksum = hashlib.sha256(snapshot_blob).hexdigest()
    
    # Update quality score and drift score on the batch
    db_conn.execute("BEGIN IMMEDIATE")
    cursor.execute(
        """
        UPDATE import_batches 
        SET drift_score = ?, quality_score = ?, validated_payload_snapshot = ?, snapshot_checksum = ?, updated_at = datetime('now')
        WHERE batch_id = ?
        """,
        (drift_score, quality_score, snapshot_blob, snapshot_checksum, batch_id)
    )
    db_conn.commit()
    
    # Populate Staging & Logs
    db_conn.execute("BEGIN IMMEDIATE")
    for p in payload_list:
        std_vals = p["standardized_values"]
        row_errs = p["validation_errors"]
        row_idx = p["source_row_index"]
        
        # Staging row status is VALID iff no CRITICAL or ERROR severity issues
        is_row_valid = not any(e["severity"] in {"CRITICAL", "ERROR"} for e in row_errs)
        val_status = "VALID" if is_row_valid else "INVALID"
        
        cursor.execute(
            """
            INSERT INTO staging_inventory_imports (
                import_batch_id, company_id, region_code, product_name, date, quantity, validation_status, source_row_index
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (batch_id, company_id, std_vals["region_code"], std_vals["product_name"], std_vals["date"], std_vals["quantity"], val_status, row_idx)
        )
        
        # Save validation errors in log
        for err in row_errs:
            cursor.execute(
                """
                INSERT INTO excel_parse_logs (
                    import_batch_id, company_id, severity, message, column_name, row_index
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (batch_id, company_id, err["severity"], err["message"], err["column"], row_idx)
            )
    db_conn.commit()
    
    # 8. Bypass Policy Checks
    # Auto-approve IFF DriftScore < 0.2 AND no Critical/Error severity issues
    if drift_score < 0.2 and not has_critical and not has_error:
        # Determine transition history audit reason
        reason_text = "Bypass automatic approval: perfect schema alignment with zero hard validation errors."
        if has_warning:
            warning_count = sum(1 for p in payload_list for e in p["validation_errors"] if e["severity"] == "WARNING")
            reason_text = json.dumps({"auto_approved_warnings": True, "warning_count": warning_count})
            
        version = transition_batch_status(
            db_conn, batch_id, BatchStatus.APPROVED, version, BatchStatus.PARSED,
            changed_by, reason_text
        )
        return batch_id, BatchStatus.APPROVED
        
    elif has_critical:
        # Hard fail immediately
        version = transition_batch_status(
            db_conn, batch_id, BatchStatus.FAILED, version, BatchStatus.PARSED,
            changed_by, "Automatic ingestion aborted: critical validation errors detected."
        )
        return batch_id, BatchStatus.FAILED
        
    else:
        # Shift to REVIEW_REQUIRED
        version = transition_batch_status(
            db_conn, batch_id, BatchStatus.REVIEW_REQUIRED, version, BatchStatus.PARSED,
            changed_by, f"Batch diverted to Review: DriftScore ({drift_score}) or validation warnings/errors present."
        )
        return batch_id, BatchStatus.REVIEW_REQUIRED
