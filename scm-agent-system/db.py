# db.py
"""
db.py
-----
Facade module that re-exports all connection, migration, seeding, and caching
functionality from the utils/db package to ensure backward compatibility
across the codebase.
"""

from utils.db.connection import (
    DB_PATH,
    translate_to_postgres,
    PostgresCursorWrapper,
    PostgresConnectionWrapper,
    get_db_connection
)

from utils.db.migrations import (
    init_db,
    run_recovery_scanner
)

from utils.db.seed import (
    seed_initial_data
)

from utils.db.cache import (
    IdempotencyCache,
    idempotency_cache
)

def log_system_action(user_id: str, ip_address: str, event_type: str, action_details: str, prev_state: str = None, new_state: str = None, is_automated: int = 0):
    """
     audit log helper (facade bridge to keep compatibility)
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO system_audit_log (user_id, ip_address, event_type, action_details, prev_state, new_state, is_automated)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, ip_address, event_type, action_details, prev_state, new_state, is_automated)
        )
        conn.commit()
    except Exception as e:
        print(f"Failed to write audit log: {e}")
        conn.rollback()
    finally:
        conn.close()
