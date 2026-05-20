# db.py
import os
import sqlite3

# Try simulation path first, then fallback to root data path
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "simulator/data/sigma_enterprise.db"))
if not os.path.exists(DB_PATH):
    DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "data/sigma_enterprise.db"))

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

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
        conn.execute("PRAGMA foreign_keys = ON;")
        
        # 1. Ensure schema_migrations table exists
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        
        # 2. Find and apply migration scripts from migrations/ directory
        migrations_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "migrations"))
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

        # 3. Create supplementary tables not tracked in core migrations
        conn.execute("""
            CREATE TABLE IF NOT EXISTS lkv_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                state_json TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
                financial_seeds.append((prod, unit_price, financial_seeds_holding := holding_cost))
                
            cursor.executemany(
                "INSERT INTO product_financial_master (product_name, unit_price, holding_cost_per_day) VALUES (?, ?, ?)",
                financial_seeds
            )
        conn.commit()
    except Exception as e:
        print(f"Error initializing SQLite DB: {e}")
    finally:
        conn.close()


def seed_initial_data():
    """
    Clone 직후 빈 DB에 초기 운영 데이터를 자동 주입합니다.
    이미 데이터가 있는 경우 아무 작업도 수행하지 않습니다 (멱등성 보장).
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # ── 1. region_inventory 시드 ──
        cursor.execute("SELECT COUNT(*) FROM region_inventory")
        if cursor.fetchone()[0] == 0:
            csv_path = os.path.join(os.path.dirname(__file__), "data", "sample_inventory_data.csv")
            if os.path.exists(csv_path):
                import pandas as pd
                df = pd.read_csv(csv_path)

                # 한글 컬럼명 → 영문 매핑
                column_map = {"지점": "region", "상품명": "product", "수량": "quantity", "날짜": "date"}
                df.rename(columns=column_map, inplace=True)

                # 지점명 → region_code 변환
                region_name_to_code = {"서울": "KR-11", "부산": "KR-26", "제주": "KR-49"}
                df["region_code"] = df["region"].map(region_name_to_code)

                inserted = 0
                for _, row in df.iterrows():
                    if pd.notna(row.get("region_code")):
                        # sample_inventory_data.csv의 상품명 'MCU 반도체' -> '반도체 칩' 변환 필요 여부 확인
                        # DB의 product_financial_master에는 '반도체 칩'으로 되어 있으므로 상품명도 통일
                        prod_name = row["product"]
                        if prod_name == "MCU 반도체":
                            prod_name = "반도체 칩"
                        elif prod_name == "마스크":
                            prod_name = "마스크"
                        elif prod_name == "손소독제":
                            prod_name = "종합 품목"
                            
                        cursor.execute(
                            """INSERT OR IGNORE INTO region_inventory 
                               (region_code, product_name, date, quantity) 
                               VALUES (?, ?, ?, ?)""",
                            (row["region_code"], prod_name, row["date"], row["quantity"])
                        )
                        inserted += 1
                conn.commit()
                print(f"✅ [DB 시드] 초기 재고 데이터 {inserted}건 자동 주입 완료 (소스: {csv_path})")
            else:
                # ❌ 파일 부재 시 명시적 경고 출력
                print(f"⚠️ [DB 시드 실패] 초기 데이터 파일 없음: {csv_path}")
                print(f"   → region_inventory 테이블이 비어있는 상태로 시뮬레이션이 시작됩니다.")
                print(f"   → 대시보드 UI를 통해 수동으로 Excel/CSV 데이터를 주입해야 합니다.")

        # ── 2. daily_demand_stats 시드 ──
        cursor.execute("SELECT COUNT(*) FROM daily_demand_stats")
        if cursor.fetchone()[0] == 0:
            # region_inventory 데이터를 기반으로 30일 이동평균 추정 생성
            cursor.execute("""
                SELECT region_code, product_name, date, quantity
                FROM region_inventory
                ORDER BY region_code, product_name, date
            """)
            rows = cursor.fetchall()

            if rows:
                inserted = 0
                for row in rows:
                    cursor.execute(
                        """INSERT OR IGNORE INTO daily_demand_stats 
                           (region_code, product_name, date, daily_outbound_total, moving_avg_30d) 
                           VALUES (?, ?, ?, ?, ?)""",
                        (row[0], row[1], row[2],
                         row[3] * 0.03,  # 일 출고량 추정 (재고의 3%)
                         row[3] * 0.03)   # 초기값이므로 이동평균 = 일 출고량
                    )
                    inserted += 1
                conn.commit()
                print(f"✅ [DB 시드] 일별 수요 통계 {inserted}건 자동 생성 완료")
            else:
                print(f"⚠️ [DB 시드 실패] region_inventory가 비어있어 daily_demand_stats를 생성할 수 없습니다.")

    except Exception as e:
        print(f"❌ [DB 시드 실패] 초기 데이터 주입 중 중대한 오류 발생: {e}")
        conn.rollback()
    finally:
        conn.close()

