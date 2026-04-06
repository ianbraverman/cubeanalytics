#!/usr/bin/env python3
"""
Add player_name column to post_draft_feedback and make user_id nullable.
Run from the back_end directory: python migrate_feedback.py
"""
import os
from dotenv import load_dotenv
from sqlalchemy import text, create_engine

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set"); exit(1)

engine = create_engine(DATABASE_URL)

migrations = [
    # Make user_id nullable
    "ALTER TABLE post_draft_feedback ALTER COLUMN user_id DROP NOT NULL;",
    # Add player_name column (if it doesn't exist)
    "ALTER TABLE post_draft_feedback ADD COLUMN IF NOT EXISTS player_name VARCHAR;",
    # Fix overall_rating range: was constrained to 1-5, now allow 1-10 (constraint is enforced in app layer)
    # No DB constraint to change — range is only in the Pydantic schema.
]

with engine.connect() as conn:
    for sql in migrations:
        try:
            conn.execute(text(sql))
            print(f"  ✓ {sql.strip()}")
        except Exception as e:
            print(f"  ⚠  Skipped (may already exist): {e}")
    conn.commit()

print("\n✅ post_draft_feedback migration complete.")
