-- db/migration/V4__refine_forensic_keys.sql

DROP TABLE IF EXISTS excel_parse_logs;

CREATE TABLE excel_parse_logs (
    id BIGSERIAL PRIMARY KEY,
    import_batch_id VARCHAR(100),
    company_id VARCHAR(100) NOT NULL,
    severity VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    column_name VARCHAR(100),
    row_index INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (import_batch_id) REFERENCES import_batches (batch_id) ON DELETE RESTRICT
);

CREATE INDEX idx_batch_status_history_batch ON batch_status_history (batch_id);
