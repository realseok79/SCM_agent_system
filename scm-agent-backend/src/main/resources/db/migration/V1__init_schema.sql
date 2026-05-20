-- db/migration/V1__init_schema.sql

CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255),
    password VARCHAR(255) NOT NULL DEFAULT '$2a$10$eFytJDGtjbThXa5zF14gE.9qQ3yvXWkU8zN2wV4rE1zD0vG.i3W7.', -- 디폴트 해시 비밀번호
    role VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE regions (
    id BIGSERIAL PRIMARY KEY,
    region_name VARCHAR(100) NOT NULL UNIQUE,
    region_code VARCHAR(50) NOT NULL UNIQUE,
    description VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_region_mappings (
    user_id BIGINT,
    region_id BIGINT,
    PRIMARY KEY (user_id, region_id),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (region_id) REFERENCES regions (id) ON DELETE CASCADE
);

CREATE TABLE region_inventory (
    region_code VARCHAR(50) NOT NULL,
    product_name VARCHAR(100) NOT NULL,
    date VARCHAR(20) NOT NULL,
    quantity DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (region_code, product_name, date),
    FOREIGN KEY (region_code) REFERENCES regions (region_code) ON DELETE CASCADE
);

CREATE TABLE weather_cache (
    region_code VARCHAR(50) NOT NULL,
    date VARCHAR(20) NOT NULL,
    temp DOUBLE PRECISION,
    humidity DOUBLE PRECISION,
    precipitation DOUBLE PRECISION,
    weather_desc VARCHAR(255),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (region_code, date),
    FOREIGN KEY (region_code) REFERENCES regions (region_code) ON DELETE CASCADE
);

CREATE TABLE regional_insights (
    region_code VARCHAR(50) NOT NULL,
    date VARCHAR(20) NOT NULL,
    action_plan_msg TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (region_code, date),
    FOREIGN KEY (region_code) REFERENCES regions (region_code) ON DELETE CASCADE
);

CREATE TABLE stock_out_logs (
    id BIGSERIAL PRIMARY KEY,
    region_code VARCHAR(50) NOT NULL,
    product_name VARCHAR(100) NOT NULL,
    outbound_qty DOUBLE PRECISION NOT NULL,
    transaction_type VARCHAR(100) NOT NULL DEFAULT '정상출고',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (region_code) REFERENCES regions (region_code) ON DELETE CASCADE
);

CREATE TABLE daily_demand_stats (
    region_code VARCHAR(50) NOT NULL,
    product_name VARCHAR(100) NOT NULL,
    date VARCHAR(20) NOT NULL,
    daily_outbound_total DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    moving_avg_30d DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    PRIMARY KEY (region_code, product_name, date),
    FOREIGN KEY (region_code) REFERENCES regions (region_code) ON DELETE CASCADE
);

CREATE TABLE product_financial_master (
    product_name VARCHAR(100) PRIMARY KEY,
    unit_price INTEGER NOT NULL,
    holding_cost_per_day DOUBLE PRECISION NOT NULL
);

CREATE TABLE inventory_rebalancing_orders (
    transfer_id BIGSERIAL PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL,
    from_region VARCHAR(50) NOT NULL,
    to_region VARCHAR(50) NOT NULL,
    transfer_qty INTEGER NOT NULL,
    saved_cost INTEGER NOT NULL,
    status VARCHAR(50) DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
