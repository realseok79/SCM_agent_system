# tests/test_state_machine.py
import pytest
import sqlite3
from unittest.mock import MagicMock, PropertyMock

from utils.parser.core import (
    BatchStatus,
    validate_transition,
    transition_batch_status,
    is_transaction_active
)
from utils.parser.exceptions import (
    InvalidStateTransitionError,
    NestedTransactionError,
    ConflictError
)

def test_validate_transition_success():
    """Verify that all valid transitions defined in ALLOWED_TRANSITIONS pass validation"""
    validate_transition(BatchStatus.CREATED, BatchStatus.PARSED)
    validate_transition(BatchStatus.CREATED, BatchStatus.FAILED)
    validate_transition(BatchStatus.PARSED, BatchStatus.APPROVED)
    validate_transition(BatchStatus.PARSED, BatchStatus.REVIEW_REQUIRED)
    validate_transition(BatchStatus.PARSED, BatchStatus.FAILED)
    validate_transition(BatchStatus.REVIEW_REQUIRED, BatchStatus.APPROVED)
    validate_transition(BatchStatus.REVIEW_REQUIRED, BatchStatus.FAILED)
    validate_transition(BatchStatus.REVIEW_REQUIRED, BatchStatus.ROLLED_BACK)
    validate_transition(BatchStatus.APPROVED, BatchStatus.COMMITTED)
    validate_transition(BatchStatus.APPROVED, BatchStatus.REVOKING)
    validate_transition(BatchStatus.REVOKING, BatchStatus.REVIEW_REQUIRED)
    validate_transition(BatchStatus.REVOKING, BatchStatus.FAILED)

def test_validate_transition_invalid():
    """Verify that invalid transitions trigger InvalidStateTransitionError"""
    invalid_cases = [
        (BatchStatus.CREATED, BatchStatus.COMMITTED),
        (BatchStatus.PARSED, BatchStatus.COMMITTED),
        (BatchStatus.APPROVED, BatchStatus.APPROVED),
        (BatchStatus.COMMITTED, BatchStatus.CREATED),
        (BatchStatus.FAILED, BatchStatus.CREATED),
        (BatchStatus.ROLLED_BACK, BatchStatus.CREATED)
    ]
    for from_state, to_state in invalid_cases:
        with pytest.raises(InvalidStateTransitionError):
            validate_transition(from_state, to_state)

def test_is_transaction_active():
    """Verify is_transaction_active helper correctly identifies transaction state"""
    mock_conn = MagicMock()
    mock_conn.in_transaction = True
    assert is_transaction_active(mock_conn) is True
    
    mock_conn.in_transaction = False
    assert is_transaction_active(mock_conn) is False

def test_transition_batch_status_nested_transaction_guard():
    """Verify nested transaction guard blocks execution when a transaction is active"""
    mock_conn = MagicMock()
    mock_conn.in_transaction = True
    
    with pytest.raises(NestedTransactionError):
        transition_batch_status(
            mock_conn,
            "BATCH_123",
            BatchStatus.PARSED,
            1,
            BatchStatus.CREATED
        )

def test_transition_batch_status_success():
    """Verify successful optimistic status transition and audit history insertion"""
    mock_conn = MagicMock()
    mock_conn.in_transaction = False
    
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = ("CREATED", 1)  # status, version
    mock_conn.cursor.return_value = mock_cursor
    
    # Run transition BATCH_123 from CREATED -> PARSED
    next_ver = transition_batch_status(
        mock_conn,
        "BATCH_123",
        BatchStatus.PARSED,
        1,  # expected current version
        BatchStatus.CREATED,
        changed_by="USER_A",
        reason="Testing state change"
    )
    
    assert next_ver == 2
    mock_cursor.execute.assert_any_call(
        "SELECT status, version FROM import_batches WHERE batch_id = ?",
        ("BATCH_123",)
    )
    mock_conn.commit.assert_called_once()

def test_transition_batch_status_conflict_version():
    """Verify ConflictError is raised on version mismatch (optimistic lock violation)"""
    mock_conn = MagicMock()
    # in_transaction: 초기 False (진입 허용) → BEGIN IMMEDIATE 이후 True (rollback 조건 충족)
    type(mock_conn).in_transaction = PropertyMock(side_effect=[False, True])
    
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = ("CREATED", 5)  # Current DB version is 5, but we expect 1
    mock_conn.cursor.return_value = mock_cursor
    
    with pytest.raises(ConflictError) as exc:
        transition_batch_status(
            mock_conn,
            "BATCH_123",
            BatchStatus.PARSED,
            1,  # expected version
            BatchStatus.CREATED
        )
    assert "Version mismatch" in str(exc.value)
    mock_conn.rollback.assert_called_once()

def test_transition_batch_status_conflict_status():
    """Verify ConflictError is raised on status mismatch"""
    mock_conn = MagicMock()
    # in_transaction: 초기 False (진입 허용) → BEGIN IMMEDIATE 이후 True (rollback 조건 충족)
    type(mock_conn).in_transaction = PropertyMock(side_effect=[False, True])
    
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = ("FAILED", 1)  # DB status is FAILED, but we expect CREATED
    mock_conn.cursor.return_value = mock_cursor
    
    with pytest.raises(ConflictError) as exc:
        transition_batch_status(
            mock_conn,
            "BATCH_123",
            BatchStatus.PARSED,
            1,
            BatchStatus.CREATED
        )
    assert "Status mismatch" in str(exc.value)
    mock_conn.rollback.assert_called_once()
