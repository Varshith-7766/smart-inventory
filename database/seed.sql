-- =============================================================================
-- seed.sql
-- Loads the schema then populates sample data.
-- Usage:  mysql -u root -p < database/seed.sql
-- =============================================================================

SOURCE database/schema.sql;

-- Additional sample data can go here for environment-specific seeding.
-- The schema.sql already includes 50+ INSERT records for all 8 tables.
-- Run this file to get a fully populated dev database.
