-- V19__add_region_inventory_indices.sql
CREATE INDEX idx_inventory_date ON region_inventory (date);
CREATE INDEX idx_inventory_region_product ON region_inventory (region_code, product_name);
