-- Setup script for Cube Foundry database
-- Run this with: psql -U postgres -f setup_db.sql

-- Create database
CREATE DATABASE cube_foundry;

-- Create user
CREATE USER cube_user WITH PASSWORD 'cube_foundry';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE cube_foundry TO cube_user;

-- Connect to the database and grant schema privileges
\c cube_foundry
GRANT ALL ON SCHEMA public TO cube_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO cube_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO cube_user;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO cube_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO cube_user;
