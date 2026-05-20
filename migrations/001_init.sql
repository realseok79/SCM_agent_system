-- migrations/001_init.sql

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT,
    role TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS regions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    region_name TEXT NOT NULL UNIQUE,
    region_code TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_region_mappings (
    user_id INTEGER,
    region_id INTEGER,
    PRIMARY KEY (user_id, region_id),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (region_id) REFERENCES regions (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS region_inventory (
    region_code TEXT NOT NULL,
    product_name TEXT NOT NULL,
    date TEXT NOT NULL,
    quantity REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (region_code, product_name, date),
    FOREIGN KEY (region_code) REFERENCES regions (region_code) ON DELETE CASCADE
);

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
);

CREATE TABLE IF NOT EXISTS regional_insights (
    region_code TEXT NOT NULL,
    date TEXT NOT NULL,
    action_plan_msg TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (region_code, date),
    FOREIGN KEY (region_code) REFERENCES regions (region_code) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS stock_out_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    region_code TEXT NOT NULL,
    product_name TEXT NOT NULL,
    outbound_qty REAL NOT NULL,
    transaction_type TEXT NOT NULL DEFAULT '정상출고',
    timestamp TIMESTAMP DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (region_code) REFERENCES regions (region_code) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS daily_demand_stats (
    region_code TEXT NOT NULL,
    product_name TEXT NOT NULL,
    date TEXT NOT NULL,
    daily_outbound_total REAL NOT NULL DEFAULT 0.0,
    moving_avg_30d REAL NOT NULL DEFAULT 0.0,
    PRIMARY KEY (region_code, product_name, date),
    FOREIGN KEY (region_code) REFERENCES regions (region_code) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS product_financial_master (
    product_name TEXT PRIMARY KEY,
    unit_price INTEGER NOT NULL,
    holding_cost_per_day REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS inventory_rebalancing_orders (
    transfer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT NOT NULL,
    from_region TEXT NOT NULL,
    to_region TEXT NOT NULL,
    transfer_qty INTEGER NOT NULL,
    saved_cost INTEGER NOT NULL,
    status TEXT DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
