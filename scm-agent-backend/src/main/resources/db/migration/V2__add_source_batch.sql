-- db/migration/V2__add_source_batch.sql

ALTER TABLE region_inventory ADD COLUMN source_batch_id VARCHAR(100) NOT NULL DEFAULT 'SEED_DATA';
CREATE INDEX idx_region_inventory_source_batch ON region_inventory (source_batch_id);
