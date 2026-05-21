-- migrations/006_add_source_to_insight.sql
ALTER TABLE regional_insights ADD COLUMN source TEXT DEFAULT 'RULE_ENGINE';
