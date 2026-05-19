# db.py
import os
import sqlite3

DB_PATH = "data/sigma_enterprise.db"

def get_db_connection():
    """
    SQLite 데이터베이스 커넥션을 반환합니다.
    동시성 문제 해결을 위해 WAL(Write-Ahead Logging) 모드와 busy_timeout을 적용합니다.
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    
    # ── [동시성 보완] WAL 모드 및 busy_timeout 설정 ──
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """
    필요한 모든 데이터베이스 테이블을 초기화합니다.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. 사용자 테이블 (users)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT,
                role TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 2. 지역 테이블 (regions)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS regions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                region_name TEXT NOT NULL UNIQUE,
                region_code TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 3. 사용자-지역 권한 매핑 테이블 (user_region_mappings)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_region_mappings (
                user_id INTEGER,
                region_id INTEGER,
                PRIMARY KEY (user_id, region_id),
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (region_id) REFERENCES regions (id) ON DELETE CASCADE
            )
        """)
        
        # 4. 지역별 상품 일별 재고/수요 테이블 (region_inventory) - Composite PK 적용
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS region_inventory (
                region_code TEXT NOT NULL,
                product_name TEXT NOT NULL,
                date TEXT NOT NULL,
                quantity REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (region_code, product_name, date),
                FOREIGN KEY (region_code) REFERENCES regions (region_code) ON DELETE CASCADE
            )
        """)
        
        # 5. 외부 날씨 데이터 캐시 테이블 (weather_cache) - Composite PK 적용
        cursor.execute("""
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
            )
        """)
        
        conn.commit()
        
        # ── [안정화 배포 보완] 기본 데이터 자동 시드 (Seeding) ──
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
        conn.commit()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully with WAL mode.")
