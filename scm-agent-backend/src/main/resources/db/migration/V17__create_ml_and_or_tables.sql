-- db/migration/V17__create_ml_and_or_tables.sql

CREATE TABLE item_master (
    product_name VARCHAR(100) PRIMARY KEY REFERENCES product_financial_master(product_name) ON DELETE CASCADE,
    abc_class VARCHAR(1) NOT NULL CHECK (abc_class IN ('A', 'B', 'C')),
    holding_cost_rate DOUBLE PRECISION NOT NULL DEFAULT 0.2000,
    ordering_cost_fixed DOUBLE PRECISION NOT NULL DEFAULT 10000.00,
    base_lead_time_days INTEGER NOT NULL DEFAULT 3,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ml_inference_logs (
    inference_id BIGSERIAL PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL REFERENCES product_financial_master(product_name) ON DELETE CASCADE,
    region_code VARCHAR(50) NOT NULL REFERENCES regions(region_code) ON DELETE CASCADE,
    target_date VARCHAR(20) NOT NULL,
    predicted_demand_10 DOUBLE PRECISION NOT NULL,
    predicted_demand_50 DOUBLE PRECISION NOT NULL,
    predicted_demand_90 DOUBLE PRECISION NOT NULL,
    shap_values JSONB NOT NULL,
    model_version VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
