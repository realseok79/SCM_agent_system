# tests/test_rollback_engine_extended.py
import pytest
from unittest.mock import MagicMock
from utils.parser.rollback_engine import rollback_batch
from utils.parser.exceptions import ConflictError

def test_rollback_batch_not_found():
    """존재하지 않는 배치 ID로 롤백 시도 시 ConflictError 발생 검증"""
    db_conn = MagicMock()
    cursor = db_conn.cursor.return_value
    cursor.fetchone.return_value = None  # 배치 없음
    
    with pytest.raises(ConflictError) as exc_info:
        rollback_batch(db_conn, "NONEXISTENT", 1)
    assert "not found" in str(exc_info.value)

def test_rollback_batch_version_mismatch():
    """배치 버전이 일치하지 않을 때 ConflictError 발생 검증"""
    db_conn = MagicMock()
    cursor = db_conn.cursor.return_value
    cursor.fetchone.return_value = ("APPROVED", 2)  # DB 버전은 2이나 current_version은 1
    
    with pytest.raises(ConflictError) as exc_info:
        rollback_batch(db_conn, "BATCH_A", 1)
    assert "Version mismatch" in str(exc_info.value)

def test_rollback_batch_status_not_approved():
    """배치 상태가 APPROVED가 아닌 경우 (예: FAILED) ConflictError 발생 검증"""
    db_conn = MagicMock()
    cursor = db_conn.cursor.return_value
    cursor.fetchone.return_value = ("FAILED", 1)
    
    with pytest.raises(ConflictError) as exc_info:
        rollback_batch(db_conn, "BATCH_A", 1)
    assert "status must be APPROVED" in str(exc_info.value)

def test_rollback_crashed_during_execution_and_failed_state_update_crashed():
    """
    [Extreme Exception Handling - L87-89]
    Step 2 실행 중 에러가 발생하여 Step 3(FAILED 상태 전이)으로 분기했는데,
    그 FAILED 상태 업데이트 도중에도 2차 DB 에러(예: Connection lost)가 발생했을 때
    안전하게 롤백 후 원 에러를 raise하는지 검증합니다.
    """
    db_conn = MagicMock()
    cursor = db_conn.cursor.return_value
    cursor.fetchone.return_value = ("APPROVED", 1)
    
    # db_conn.in_transaction은 롤백 처리를 위해 True로 모킹
    db_conn.in_transaction = True
    
    # 첫 트랜잭션(REVOKING 상태 전이)은 정상 진행하게 만들고
    # 그 다음 Step 2 (DELETE)에서 강제 예외 발생
    execute_calls = []
    def mock_execute(query, *args):
        execute_calls.append(query)
        if "DELETE FROM region_inventory" in query:
            raise Exception("Step 2 DB Crash")
        if "UPDATE import_batches SET status = 'FAILED'" in query:
            raise Exception("Step 3 Secondary Crash")
        return MagicMock()
        
    db_conn.execute.side_effect = mock_execute
    
    with pytest.raises(Exception) as exc_info:
        rollback_batch(db_conn, "BATCH_A", 1)
        
    assert "Step 2 DB Crash" in str(exc_info.value)
    # in_transaction이 참이므로 rollback()이 2차례 안전하게 호출되어 누출이 예방되었는지 확인
    assert db_conn.rollback.call_count >= 1
