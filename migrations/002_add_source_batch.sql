-- migrations/002_add_source_batch.sql

ALTER TABLE region_inventory ADD COLUMN source_batch_id TEXT NOT NULL DEFAULT 'SEED_DATA';
CREATE INDEX IF NOT EXISTS idx_region_inventory_source_batch ON region_inventory (source_batch_id);
