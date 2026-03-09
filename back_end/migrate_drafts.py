"""
Migration: Add draft + deck enrichment columns
Run once: python migrate_drafts.py
"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost/cubeanalytics")

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True
cur = conn.cursor()

columns = [
    # draft_events enrichment
    ("draft_events", "name",           "VARCHAR(200)"),
    ("draft_events", "status",         "VARCHAR(20) DEFAULT 'active'"),
    ("draft_events", "num_players",    "INTEGER DEFAULT 0"),
    ("draft_events", "ai_summary",     "TEXT"),
    # user_decks enrichment
    ("user_decks",   "player_name",    "VARCHAR(100)"),
    ("user_decks",   "deck_name",      "VARCHAR(200)"),
    ("user_decks",   "wins",           "INTEGER DEFAULT 0"),
    ("user_decks",   "losses",         "INTEGER DEFAULT 0"),
    ("user_decks",   "deck_photo_url", "VARCHAR(500)"),
    ("user_decks",   "ai_description", "TEXT"),
    ("user_decks",   "full_pool_cards","TEXT"),
]

for table, col, col_type in columns:
    try:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {col_type};")
        print(f"  ✓ {table}.{col}")
    except Exception as e:
        print(f"  ✗ {table}.{col}: {e}")

# Make record nullable (existing rows may have empty string)
try:
    cur.execute("ALTER TABLE user_decks ALTER COLUMN record DROP NOT NULL;")
    print("  ✓ user_decks.record made nullable")
except Exception as e:
    print(f"  ~ user_decks.record: {e}")

cur.close()
conn.close()
print("Migration complete.")
