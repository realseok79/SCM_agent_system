-- 007_scm_domain_extensions.sql

-- 1. Suppliers Table
CREATE TABLE IF NOT EXISTS suppliers (
    supplier_code TEXT PRIMARY KEY,
    supplier_name TEXT NOT NULL,
    service_rating TEXT NOT NULL DEFAULT 'B',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Lead Time Matrix Table
CREATE TABLE IF NOT EXISTS lead_time_matrix (
    supplier_code TEXT NOT NULL,
    product_name TEXT NOT NULL,
    logistics_mode TEXT NOT NULL, -- ROAD, AIR, SEA
    lead_time_days REAL NOT NULL,
    PRIMARY KEY (supplier_code, product_name, logistics_mode),
    FOREIGN KEY (supplier_code) REFERENCES suppliers (supplier_code) ON DELETE CASCADE
);

-- 3. Add abc_class to product_financial_master
ALTER TABLE product_financial_master ADD COLUMN abc_class TEXT DEFAULT 'B';

-- 4. Forecast Accuracy Logs Table
CREATE TABLE IF NOT EXISTS forecast_accuracy_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    product_name TEXT NOT NULL,
    predicted_demand REAL NOT NULL,
    actual_demand REAL NOT NULL,
    mape REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Seed default suppliers
INSERT OR IGNORE INTO suppliers (supplier_code, supplier_name, service_rating) VALUES
('SUPPLIER_001', 'Alpha Semiconductor Corp', 'A'),
('SUPPLIER_002', 'Beta Global Logistics & Goods', 'B'),
('SUPPLIER_003', 'Gamma Health & Mask Factory', 'A');

-- 6. Seed lead time matrix entries
INSERT OR IGNORE INTO lead_time_matrix (supplier_code, product_name, logistics_mode, lead_time_days) VALUES
('SUPPLIER_001', '반도체 칩', 'ROAD', 3.5),
('SUPPLIER_001', '반도체 칩', 'AIR', 1.5),
('SUPPLIER_001', '반도체 칩', 'SEA', 9.0),
('SUPPLIER_002', '종합 품목', 'ROAD', 5.0),
('SUPPLIER_002', '종합 품목', 'AIR', 2.5),
('SUPPLIER_002', '종합 품목', 'SEA', 12.0),
('SUPPLIER_003', '마스크', 'ROAD', 2.0),
('SUPPLIER_003', '마스크', 'AIR', 1.0),
('SUPPLIER_003', '마스크', 'SEA', 7.0);

-- 7. Update ABC classification for existing products
UPDATE product_financial_master SET abc_class = 'A' WHERE product_name = '반도체 칩';
UPDATE product_financial_master SET abc_class = 'B' WHERE product_name = '종합 품목';
UPDATE product_financial_master SET abc_class = 'C' WHERE product_name = '마스크';
