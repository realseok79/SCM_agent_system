-- db/migration/V3__add_parse_logs.sql

CREATE TABLE import_batches (
    batch_id VARCHAR(100) PRIMARY KEY,
    company_id VARCHAR(100) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_sha256 VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    drift_score DOUBLE PRECISION,
    quality_score DOUBLE PRECISION,
    validated_payload_snapshot BYTEA, -- BLOB -> BYTEA
    snapshot_checksum VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    parsed_at TIMESTAMP,
    reviewed_at TIMESTAMP,
    committed_at TIMESTAMP,
    failed_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_drift_score CHECK (drift_score IS NULL OR (drift_score >= 0.0 AND drift_score <= 1.0)),
    CONSTRAINT chk_quality_score CHECK (quality_score IS NULL OR (quality_score >= 0.0 AND quality_score <= 1.0))
);

CREATE TABLE staging_inventory_imports (
    id BIGSERIAL PRIMARY KEY,
    import_batch_id VARCHAR(100) NOT NULL,
    company_id VARCHAR(100) NOT NULL,
    region_code VARCHAR(50),
    product_name VARCHAR(100),
    date VARCHAR(20),
    quantity DOUBLE PRECISION,
    validation_status VARCHAR(50),
    source_row_index INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (import_batch_id) REFERENCES import_batches (batch_id) ON DELETE CASCADE
);

CREATE TABLE excel_parse_logs (
    id BIGSERIAL PRIMARY KEY,
    import_batch_id VARCHAR(100),
    company_id VARCHAR(100) NOT NULL,
    severity VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    column_name VARCHAR(100),
    row_index INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (import_batch_id) REFERENCES import_batches (batch_id) ON DELETE CASCADE
);

CREATE TABLE batch_status_history (
    id BIGSERIAL PRIMARY KEY,
    batch_id VARCHAR(100) NOT NULL,
    from_status VARCHAR(50),
    to_status VARCHAR(50) NOT NULL,
    changed_by VARCHAR(100) NOT NULL,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (batch_id) REFERENCES import_batches (batch_id) ON DELETE CASCADE
);

CREATE TABLE company_excel_mapping (
    company_id VARCHAR(100) NOT NULL,
    raw_header VARCHAR(100) NOT NULL,
    mapped_column VARCHAR(100) NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    negative_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (company_id, raw_header, mapped_column),
    CONSTRAINT chk_confidence CHECK (confidence >= 0.0 AND confidence <= 1.0),
    CONSTRAINT chk_negative_score CHECK (negative_score >= 0.0)
);
