-- migrations/005_add_risk_fields_to_insight.sql
ALTER TABLE regional_insights ADD COLUMN risk_score REAL;
ALTER TABLE regional_insights ADD COLUMN risk_level TEXT;
ALTER TABLE regional_insights ADD COLUMN description TEXT;
