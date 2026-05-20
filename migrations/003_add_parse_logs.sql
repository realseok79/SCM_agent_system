-- migrations/003_add_parse_logs.sql

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
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_drift_score CHECK (drift_score IS NULL OR (drift_score >= 0.0 AND drift_score <= 1.0)),
    CONSTRAINT chk_quality_score CHECK (quality_score IS NULL OR (quality_score >= 0.0 AND quality_score <= 1.0))
);

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

CREATE TABLE IF NOT EXISTS company_excel_mapping (
    company_id TEXT NOT NULL,
    raw_header TEXT NOT NULL,
    mapped_column TEXT NOT NULL,
    confidence REAL NOT NULL,
    negative_score REAL NOT NULL DEFAULT 0.0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (company_id, raw_header, mapped_column),
    CONSTRAINT chk_confidence CHECK (confidence >= 0.0 AND confidence <= 1.0),
    CONSTRAINT chk_negative_score CHECK (negative_score >= 0.0)
);
