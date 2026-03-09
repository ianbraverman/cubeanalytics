"""Add pool_photo_url column to user_decks."""
import os
from dotenv import load_dotenv
load_dotenv()

import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL", "")


def run():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'user_decks' AND column_name = 'pool_photo_url'
    """)
    if cur.fetchone():
        print("✓ pool_photo_url already exists, nothing to do")
    else:
        cur.execute("ALTER TABLE user_decks ADD COLUMN pool_photo_url VARCHAR(500)")
        conn.commit()
        print("✓ Added user_decks.pool_photo_url")

    cur.close()
    conn.close()


if __name__ == "__main__":
    run()
