#!/usr/bin/env python3
"""
Script to migrate the database schema by adding new card detail columns.
Run this from the back_end directory with: python migrate_schema.py
"""

import os
from dotenv import load_dotenv
from sqlalchemy import text, create_engine

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable not set")
    exit(1)

try:
    # Create engine
    engine = create_engine(DATABASE_URL)
    
    # SQL migration
    migration_sql = """
    ALTER TABLE cards 
    ADD COLUMN IF NOT EXISTS mana_cost VARCHAR,
    ADD COLUMN IF NOT EXISTS type_line VARCHAR,
    ADD COLUMN IF NOT EXISTS colors JSON,
    ADD COLUMN IF NOT EXISTS cmc FLOAT,
    ADD COLUMN IF NOT EXISTS power VARCHAR,
    ADD COLUMN IF NOT EXISTS toughness VARCHAR,
    ADD COLUMN IF NOT EXISTS oracle_text TEXT,
    ADD COLUMN IF NOT EXISTS image_url VARCHAR,
    ADD COLUMN IF NOT EXISTS small_image_url VARCHAR,
    ADD COLUMN IF NOT EXISTS rarity VARCHAR,
    ADD COLUMN IF NOT EXISTS set_code VARCHAR,
    ADD COLUMN IF NOT EXISTS set_name VARCHAR,
    ADD COLUMN IF NOT EXISTS scryfall_uri VARCHAR;
    """
    
    # Execute migration
    with engine.connect() as connection:
        connection.execute(text(migration_sql))
        connection.commit()
        print("✓ Database schema migration completed successfully!")
        print("  Added columns: mana_cost, type_line, colors, cmc, power, toughness,")
        print("                 oracle_text, image_url, small_image_url, rarity,")
        print("                 set_code, set_name, scryfall_uri")
        
except Exception as e:
    print(f"ERROR: Migration failed - {e}")
    exit(1)
