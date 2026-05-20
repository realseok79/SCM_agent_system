# utils/parser/rollback_engine.py
from utils.parser.exceptions import ConflictError

def rollback_batch(db_conn, batch_id: str, current_version: int, changed_by: str = "SYSTEM") -> int:
    """
    Rolls back the physical inventory mutations introduced by the target batch.
    Two-step transactional locking model:
    1. Lock phase: transition status to 'REVOKING' in an active write transaction.
    2. Execution phase: delete from region_inventory, transition to 'REVIEW_REQUIRED', record history in a single write transaction.
    """
    cursor = db_conn.cursor()
    try:
        # Step 1: Transition status to REVOKING (Locking Phase)
        db_conn.execute("BEGIN IMMEDIATE")
        
        cursor.execute(
            "SELECT status, version FROM import_batches WHERE batch_id = ?",
            (batch_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise ConflictError(f"Batch {batch_id} not found.")
        status, version = row[0], row[1]
        
        if version != current_version:
            raise ConflictError(f"Version mismatch. Expected: {current_version}, DB: {version}")
            
        if status != "APPROVED":
            raise ConflictError(f"Cannot rollback batch {batch_id}: status must be APPROVED, got '{status}'.")
            
        next_version = version + 1
        db_conn.execute(
            "UPDATE import_batches SET status = 'REVOKING', version = ?, updated_at = datetime('now') WHERE batch_id = ?",
            (next_version, batch_id)
        )
        db_conn.execute(
            """
            INSERT INTO batch_status_history (batch_id, from_status, to_status, changed_by, reason)
            VALUES (?, 'APPROVED', 'REVOKING', ?, 'Rollback initiated: batch status locked to REVOKING.')
            """,
            (batch_id, changed_by)
        )
        db_conn.commit()
        
        # Step 2: Physical deletion and transition to REVIEW_REQUIRED (Execution Phase)
        db_conn.execute("BEGIN IMMEDIATE")
        
        # Delete only rows introduced by this batch
        db_conn.execute(
            "DELETE FROM region_inventory WHERE source_batch_id = ?",
            (batch_id,)
        )
        
        final_version = next_version + 1
        db_conn.execute(
            "UPDATE import_batches SET status = 'REVIEW_REQUIRED', version = ?, updated_at = datetime('now') WHERE batch_id = ?",
            (final_version, batch_id)
        )
        db_conn.execute(
            """
            INSERT INTO batch_status_history (batch_id, from_status, to_status, changed_by, reason)
            VALUES (?, 'REVOKING', 'REVIEW_REQUIRED', ?, 'Rollback execution complete: physical rows removed.')
            """,
            (batch_id, changed_by)
        )
        db_conn.commit()
        return final_version
        
    except Exception as e:
        if db_conn.in_transaction:
            db_conn.rollback()
        # Step 3: Transition to FAILED on execution phase crash (REVOKING -> FAILED)
        try:
            db_conn.execute("BEGIN IMMEDIATE")
            db_conn.execute(
                "UPDATE import_batches SET status = 'FAILED', updated_at = datetime('now') WHERE batch_id = ?",
                (batch_id,)
            )
            db_conn.execute(
                """
                INSERT INTO batch_status_history (batch_id, from_status, to_status, changed_by, reason)
                VALUES (?, 'REVOKING', 'FAILED', ?, ?)
                """,
                (batch_id, changed_by, f"Rollback crashed: {e}")
            )
            db_conn.commit()
        except Exception:
            if db_conn.in_transaction:
                db_conn.rollback()
        raise e
    finally:
        cursor.close()
