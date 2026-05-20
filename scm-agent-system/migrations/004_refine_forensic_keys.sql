-- migrations/004_refine_forensic_keys.sql

DROP TABLE IF EXISTS excel_parse_logs;

CREATE TABLE excel_parse_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    import_batch_id TEXT,
    company_id TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT NOT NULL,
    column_name TEXT,
    row_index INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (import_batch_id) REFERENCES import_batches (batch_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_batch_status_history_batch ON batch_status_history (batch_id);
