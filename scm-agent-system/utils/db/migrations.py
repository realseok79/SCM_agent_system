# utils/db/migrations.py
import os
from .connection import get_db_connection

def run_recovery_scanner():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. APPROVED batches recovery
    cursor.execute("SELECT batch_id, version FROM import_batches WHERE status = 'APPROVED'")
    approved_batches = cursor.fetchall()
    
    for row in approved_batches:
        batch_id, version = row[0], row[1]
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """
                INSERT INTO region_inventory (region_code, product_name, date, quantity, source_batch_id)
                SELECT region_code, product_name, date, quantity, import_batch_id
                FROM staging_inventory_imports s
                WHERE s.import_batch_id = ?
                  AND s.validation_status = 'VALID'
                  AND NOT EXISTS (
                      SELECT 1 FROM region_inventory r 
                      WHERE r.source_batch_id = s.import_batch_id 
                        AND r.region_code = s.region_code 
                        AND r.product_name = s.product_name 
                        AND r.date = s.date
                  )
                """,
                (batch_id,)
            )
            conn.execute(
                "UPDATE import_batches SET status = 'COMMITTED', version = ? WHERE batch_id = ?",
                (version + 1, batch_id)
            )
            conn.execute(
                """
                INSERT INTO batch_status_history (batch_id, from_status, to_status, changed_by, reason)
                VALUES (?, 'APPROVED', 'COMMITTED', 'RECOVERY_SCANNER', 'Idempotent crash recovery: auto-committed APPROVED batch')
                """,
                (batch_id,)
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Recovery Scanner: Failed to recover APPROVED batch {batch_id}: {e}")
            
    # 2. REVOKING batches recovery
    cursor.execute("SELECT batch_id, version FROM import_batches WHERE status = 'REVOKING'")
    revoking_batches = cursor.fetchall()
    
    for row in revoking_batches:
        batch_id, version = row[0], row[1]
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("DELETE FROM region_inventory WHERE source_batch_id = ?", (batch_id,))
            conn.execute(
                "UPDATE import_batches SET status = 'REVIEW_REQUIRED', version = ? WHERE batch_id = ?",
                (version + 1, batch_id)
            )
            conn.execute(
                """
                INSERT INTO batch_status_history (batch_id, from_status, to_status, changed_by, reason)
                VALUES (?, 'REVOKING', 'REVIEW_REQUIRED', 'RECOVERY_SCANNER', 'Idempotent crash recovery: rolled back REVOKING batch')
                """,
                (batch_id,)
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Recovery Scanner: Failed to recover REVOKING batch {batch_id}: {e}")
            
    cursor.close()
    conn.close()

def init_db():
    conn = get_db_connection()
    try:
        # SQLite safety features
        conn.execute("PRAGMA foreign_keys = ON;")
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS system_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                ip_address TEXT,
                event_type TEXT NOT NULL,
                action_details TEXT NOT NULL,
                prev_state TEXT,
                new_state TEXT,
                is_automated INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()

        # Find and apply migration scripts from migrations/ directory
        migrations_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../migrations"))
        if os.path.exists(migrations_dir):
            migration_files = sorted([
                f for f in os.listdir(migrations_dir)
                if f.endswith(".sql") and "_" in f
            ])
            
            for file_name in migration_files:
                version = file_name.split("_")[0]
                
                # Check if this migration was already applied
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM schema_migrations WHERE version = ?", (version,))
                already_applied = cursor.fetchone()
                
                if not already_applied:
                    file_path = os.path.join(migrations_dir, file_name)
                    with open(file_path, "r", encoding="utf-8") as f:
                        sql_script = f.read()
                    
                    print(f"Applying SQLite migration: {file_name}")
                    try:
                        conn.executescript(sql_script)
                        conn.execute("INSERT INTO schema_migrations (version) VALUES (?)", (version,))
                        conn.commit()
                    except Exception as e:
                        conn.rollback()
                        print(f"Failed to apply migration {file_name}: {e}")
                        raise e

        conn.execute("""
            CREATE TABLE IF NOT EXISTS regions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                region_name TEXT UNIQUE NOT NULL,
                region_code TEXT UNIQUE NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT,
                role TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS product_financial_master (
                product_name TEXT PRIMARY KEY,
                unit_price INTEGER NOT NULL,
                holding_cost_per_day REAL NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS import_batches (
                batch_id TEXT PRIMARY KEY,
                company_id TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_sha256 TEXT NOT NULL,
                status TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                drift_score REAL,
                quality_score REAL,
                validated_payload_snapshot BLOB,
                snapshot_checksum TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                parsed_at TIMESTAMP,
                reviewed_at TIMESTAMP,
                committed_at TIMESTAMP,
                failed_at TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS region_inventory (
                region_code TEXT NOT NULL,
                product_name TEXT NOT NULL,
                date TEXT NOT NULL,
                quantity REAL NOT NULL,
                source_batch_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (region_code, product_name, date),
                FOREIGN KEY (region_code) REFERENCES regions (region_code) ON DELETE CASCADE
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_demand_stats (
                region_code TEXT NOT NULL,
                product_name TEXT NOT NULL,
                date TEXT NOT NULL,
                daily_outbound_total REAL NOT NULL DEFAULT 0.0,
                moving_avg_30d REAL NOT NULL DEFAULT 0.0,
                PRIMARY KEY (region_code, product_name, date),
                FOREIGN KEY (region_code) REFERENCES regions (region_code) ON DELETE CASCADE
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS staging_inventory_imports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                import_batch_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                region_code TEXT,
                product_name TEXT,
                date TEXT,
                quantity REAL,
                validation_status TEXT,
                source_row_index INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (import_batch_id) REFERENCES import_batches (batch_id) ON DELETE CASCADE
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS batch_status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id TEXT NOT NULL,
                from_status TEXT,
                to_status TEXT NOT NULL,
                changed_by TEXT NOT NULL,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (batch_id) REFERENCES import_batches (batch_id) ON DELETE CASCADE
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS stock_out_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                region_code TEXT NOT NULL,
                product_name TEXT NOT NULL,
                outbound_qty REAL NOT NULL,
                transaction_type TEXT NOT NULL DEFAULT '정상출고',
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (region_code) REFERENCES regions (region_code) ON DELETE CASCADE
            );
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_stock_out_logs_composite 
            ON stock_out_logs (timestamp, region_code, product_name);
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS inventory_rebalancing_orders (
                transfer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT NOT NULL,
                from_region TEXT NOT NULL,
                to_region TEXT NOT NULL,
                transfer_qty INTEGER NOT NULL,
                saved_cost INTEGER NOT NULL,
                status TEXT DEFAULT 'PENDING',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS weather_cache (
                region_code TEXT NOT NULL,
                date TEXT NOT NULL,
                temp REAL,
                humidity REAL,
                precipitation REAL,
                weather_desc TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (region_code, date),
                FOREIGN KEY (region_code) REFERENCES regions (region_code) ON DELETE CASCADE
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS regional_insights (
                region_code TEXT NOT NULL,
                date TEXT NOT NULL,
                action_plan_msg TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (region_code, date),
                FOREIGN KEY (region_code) REFERENCES regions (region_code) ON DELETE CASCADE
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS excel_parse_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                import_batch_id TEXT,
                company_id TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                column_name TEXT,
                row_index INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (import_batch_id) REFERENCES import_batches (batch_id) ON DELETE CASCADE
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS company_excel_mapping (
                company_id TEXT NOT NULL,
                raw_header TEXT NOT NULL,
                mapped_column TEXT NOT NULL,
                confidence REAL NOT NULL,
                negative_score REAL NOT NULL DEFAULT 0.0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (company_id, raw_header, mapped_column)
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS lkv_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                state_json TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS purchase_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                region_code TEXT NOT NULL,
                product_name TEXT NOT NULL,
                quantity REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING',
                rejection_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS guardrail_parameters (
                sku TEXT PRIMARY KEY,
                current_threshold REAL NOT NULL DEFAULT 1.0,
                base_threshold REAL NOT NULL DEFAULT 1.0,
                min_clip_rate REAL NOT NULL DEFAULT 0.5,
                max_clip_rate REAL NOT NULL DEFAULT 1.5,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS order_feedback_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                sku TEXT NOT NULL,
                action TEXT NOT NULL,
                reason TEXT,
                applied INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        
        # Seeding default data
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM regions")
        if cursor.fetchone()[0] == 0:
            default_regions = [
                ("서울특별시", "KR-11", "수도권 메인 물류 거점"),
                ("부산광역시", "KR-26", "영남권 물류 허브 및 항만 거점"),
                ("제주특별자치도", "KR-49", "제주도 물류 허브")
            ]
            cursor.executemany(
                "INSERT INTO regions (region_name, region_code, description) VALUES (?, ?, ?)",
                default_regions
            )
            
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO users (username, email, role) VALUES (?, ?, ?)",
                ("admin", "admin@sigma-enterprise.com", "ADMIN")
            )
            
        cursor.execute("SELECT COUNT(*) FROM product_financial_master")
        if cursor.fetchone()[0] == 0:
            import numpy as np
            np.random.seed(42)
            
            target_products = {
                "마스크": (np.log(500), 0.1),
                "반도체 칩": (np.log(50000), 0.2),
                "종합 품목": (np.log(10000), 0.15)
            }
            
            financial_seeds = []
            for prod, (mu, sigma) in target_products.items():
                unit_price = int(round(np.random.lognormal(mu, sigma)))
                holding_cost = round(unit_price * 0.002, 2)
                financial_seeds.append((prod, unit_price, holding_cost))
                
            cursor.executemany(
                "INSERT INTO product_financial_master (product_name, unit_price, holding_cost_per_day) VALUES (?, ?, ?)",
                financial_seeds
            )
            
        cursor.execute("SELECT COUNT(*) FROM guardrail_parameters")
        if cursor.fetchone()[0] == 0:
            default_guardrails = [
                ("마스크", 1.0, 1.0, 0.5, 1.5),
                ("반도체 칩", 1.0, 1.0, 0.5, 1.5),
                ("종합 품목", 1.0, 1.0, 0.5, 1.5)
            ]
            cursor.executemany(
                "INSERT INTO guardrail_parameters (sku, current_threshold, base_threshold, min_clip_rate, max_clip_rate) VALUES (?, ?, ?, ?, ?)",
                default_guardrails
            )
        conn.commit()
    except Exception as e:
        print(f"Error initializing SQLite DB: {e}")
    finally:
        conn.close()
