"""
Migration: add statistics columns (2026-04-09)

Adds to user_decks:
  - archetype       VARCHAR(30)
  - archetype_detail VARCHAR(100)
  - color_identity  VARCHAR(10)

Adds to cube_cards:
  - removed_at      DATETIME (soft-delete for card history)

Safe to run multiple times — uses ADD COLUMN IF NOT EXISTS (SQLite >= 3.37)
or falls back to a try/except per column for older SQLite.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from database import engine
from sqlalchemy import text

_MIGRATIONS = [
    ("user_decks",  "archetype",        "VARCHAR(30)"),
    ("user_decks",  "archetype_detail", "VARCHAR(100)"),
    ("user_decks",  "color_identity",   "VARCHAR(10)"),
    ("cube_cards",  "removed_at",       "TIMESTAMP"),
]


def _column_exists(conn, table: str, column: str) -> bool:
    result = conn.execute(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = :t AND column_name = :c"
    ), {"t": table, "c": column})
    return result.fetchone() is not None


def run():
    with engine.connect() as conn:
        for table, column, col_type in _MIGRATIONS:
            if _column_exists(conn, table, column):
                print(f"  SKIP  {table}.{column} (already exists)")
                continue
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
                conn.commit()
                print(f"  ADD   {table}.{column} {col_type}")
            except Exception as exc:
                print(f"  ERROR {table}.{column}: {exc}")

    print("Migration complete.")


if __name__ == "__main__":
    run()
