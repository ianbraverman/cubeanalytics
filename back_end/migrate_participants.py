"""Add draft_participants table."""
import os
from dotenv import load_dotenv
load_dotenv()

import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL", "")


def run():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_name = 'draft_participants'
    """)
    if cur.fetchone():
        print("✓ draft_participants already exists, nothing to do")
    else:
        cur.execute("""
            CREATE TABLE draft_participants (
                id SERIAL PRIMARY KEY,
                draft_event_id INTEGER NOT NULL REFERENCES draft_events(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                joined_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(draft_event_id, user_id)
            )
        """)
        conn.commit()
        print("✓ Created draft_participants table")

    cur.close()
    conn.close()


if __name__ == "__main__":
    run()
