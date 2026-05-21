-- db/migration/V12__add_risk_fields_to_insight.sql
ALTER TABLE regional_insights ADD COLUMN IF NOT EXISTS risk_score DOUBLE PRECISION;
ALTER TABLE regional_insights ADD COLUMN IF NOT EXISTS risk_level VARCHAR(50);
ALTER TABLE regional_insights ADD COLUMN IF NOT EXISTS description VARCHAR(255);
