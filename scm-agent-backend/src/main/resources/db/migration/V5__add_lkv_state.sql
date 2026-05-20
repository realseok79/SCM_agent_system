-- db/migration/V5__add_lkv_state.sql

CREATE TABLE lkv_state (
    company_id VARCHAR(50) NOT NULL,
    country VARCHAR(100) NOT NULL,
    state_data JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (company_id, country)
);
