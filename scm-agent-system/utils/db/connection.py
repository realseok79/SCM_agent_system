# utils/db/connection.py
import os
import re
import sqlite3

# Resolve DB path relative to utils/db package
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../simulator/data/sigma_enterprise.db"))
if not os.path.exists(DB_PATH):
    DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/sigma_enterprise.db"))

def translate_to_postgres(sql):
    if not sql:
        return sql
    # Skip PRAGMA commands
    if sql.strip().upper().startswith("PRAGMA"):
        return ""
    # Replace SQLite INTEGER PRIMARY KEY AUTOINCREMENT
    sql = re.sub(r"\bINTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT\b", "SERIAL PRIMARY KEY", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bAUTOINCREMENT\b", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bREAL\b", "DOUBLE PRECISION", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bBLOB\b", "BYTEA", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bdatetime\('now',\s*'localtime'\)\b", "CURRENT_TIMESTAMP", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bdatetime\('now'\)\b", "CURRENT_TIMESTAMP", sql, flags=re.IGNORECASE)
    
    # Translate INSERT OR IGNORE INTO table (...) VALUES (...)
    # to INSERT INTO table (...) VALUES (...) ON CONFLICT DO NOTHING
    pattern = r"INSERT\s+OR\s+IGNORE\s+INTO\s+(\w+)\s*\((.*?)\)\s*VALUES\s*\((.*?)\)"
    def repl(m):
        return f"INSERT INTO {m.group(1)} ({m.group(2)}) VALUES ({m.group(3)}) ON CONFLICT DO NOTHING"
    sql = re.sub(pattern, repl, sql, flags=re.IGNORECASE | re.DOTALL)
    sql = re.sub(r"\bINSERT\s+OR\s+IGNORE\s+INTO\b", "INSERT INTO", sql, flags=re.IGNORECASE)
    
    # Handle BEGIN IMMEDIATE / BEGIN EXCLUSIVE
    if sql.strip().upper() in ("BEGIN IMMEDIATE", "BEGIN EXCLUSIVE"):
        return "BEGIN"
        
    return sql

class PostgresCursorWrapper:
    def __init__(self, raw_cursor):
        self.raw_cursor = raw_cursor
        
    def execute(self, query, params=None):
        translated = translate_to_postgres(query)
        if not translated.strip():
            return self
        translated = translated.replace("?", "%s")
        self.raw_cursor.execute(translated, params)
        return self
        
    def executescript(self, sql_script):
        # Split by semicolon and run each
        for statement in sql_script.split(";"):
            if statement.strip():
                self.execute(statement)
        return self
        
    def executemany(self, query, params_list):
        translated = translate_to_postgres(query)
        if not translated.strip():
            return self
        translated = translated.replace("?", "%s")
        self.raw_cursor.executemany(translated, params_list)
        return self
        
    def fetchone(self):
        row = self.raw_cursor.fetchone()
        return row
        
    def fetchall(self):
        return self.raw_cursor.fetchall()
        
    @property
    def lastrowid(self):
        try:
            self.raw_cursor.execute("SELECT LASTVAL()")
            row = self.raw_cursor.fetchone()
            return row[0] if row else None
        except Exception:
            return None
            
    def close(self):
        self.raw_cursor.close()

class PostgresConnectionWrapper:
    def __init__(self, raw_conn):
        self.raw_conn = raw_conn
        
    def cursor(self):
        from psycopg2.extras import DictCursor
        return PostgresCursorWrapper(self.raw_conn.cursor(cursor_factory=DictCursor))
        
    def commit(self):
        self.raw_conn.commit()
        
    def rollback(self):
        self.raw_conn.rollback()
        
    def close(self):
        self.raw_conn.close()
        
    def execute(self, query, params=None):
        cur = self.cursor()
        cur.execute(query, params)
        return cur
        
    def executescript(self, sql_script):
        cur = self.cursor()
        cur.executescript(sql_script)
        cur.close()
        
    def executemany(self, query, params_list):
        cur = self.cursor()
        cur.executemany(query, params_list)
        return cur

def get_db_connection():
    db_type = os.getenv("DB_TYPE", "sqlite").lower()
    db_url = os.getenv("DB_URL", "")
    
    if db_type == "postgresql" or "postgresql" in db_url:
        try:
            import psycopg2
            if db_url:
                clean_url = db_url.replace("jdbc:", "")
            else:
                pg_user = os.getenv("DB_USERNAME", "scm_admin")
                pg_pass = os.getenv("DB_PASSWORD", "scm_secret_password")
                pg_host = os.getenv("DB_HOST", "localhost")
                pg_port = os.getenv("DB_PORT", "5432")
                pg_name = os.getenv("DB_NAME", "scm_enterprise")
                clean_url = f"postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_name}"
            conn = psycopg2.connect(clean_url)
            return PostgresConnectionWrapper(conn)
        except Exception as e:
            print(f"PostgreSQL connection failed: {e}. Falling back to sqlite3.")
            
    # Resolve DB_PATH dynamically to support test monkeypatching on the db facade module
    import sys
    db_path = DB_PATH
    if "db" in sys.modules:
        db_mod = sys.modules["db"]
        if hasattr(db_mod, "DB_PATH"):
            db_path = db_mod.DB_PATH
            
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
