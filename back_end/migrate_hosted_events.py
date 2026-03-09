#!/usr/bin/env python3
"""
Migration: Add hosted event, cube settings, seating, rounds, pairings, and feedback tables.
Run from back_end directory:  python migrate_hosted_events.py
"""
import os
from dotenv import load_dotenv
from sqlalchemy import text, create_engine

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set"); exit(1)

engine = create_engine(DATABASE_URL)

MIGRATIONS = [
    # ── Cube settings columns ─────────────────────────────────────────────────
    """
    ALTER TABLE cubes
        ADD COLUMN IF NOT EXISTS life_total       INTEGER   NOT NULL DEFAULT 20,
        ADD COLUMN IF NOT EXISTS pack_count       INTEGER   NOT NULL DEFAULT 3,
        ADD COLUMN IF NOT EXISTS pack_size        INTEGER   NOT NULL DEFAULT 15,
        ADD COLUMN IF NOT EXISTS draft_rules      TEXT,
        ADD COLUMN IF NOT EXISTS gameplay_rules   TEXT;
    """,
    # ── DraftEvent hosted fields ──────────────────────────────────────────────
    """
    ALTER TABLE draft_events
        ADD COLUMN IF NOT EXISTS event_type     VARCHAR(20)  NOT NULL DEFAULT 'casual',
        ADD COLUMN IF NOT EXISTS num_rounds     INTEGER,
        ADD COLUMN IF NOT EXISTS best_of        INTEGER      NOT NULL DEFAULT 1,
        ADD COLUMN IF NOT EXISTS current_round  INTEGER      NOT NULL DEFAULT 0;
    """,
    # ── Draft seats ───────────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS draft_seats (
        id              SERIAL PRIMARY KEY,
        draft_event_id  INTEGER NOT NULL REFERENCES draft_events(id) ON DELETE CASCADE,
        user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        seat_number     INTEGER NOT NULL,
        created_at      TIMESTAMP NOT NULL DEFAULT NOW()
    );
    """,
    # ── Draft rounds ──────────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS draft_rounds (
        id              SERIAL PRIMARY KEY,
        draft_event_id  INTEGER NOT NULL REFERENCES draft_events(id) ON DELETE CASCADE,
        round_number    INTEGER NOT NULL,
        status          VARCHAR(20) NOT NULL DEFAULT 'active',
        created_at      TIMESTAMP NOT NULL DEFAULT NOW()
    );
    """,
    # ── Draft pairings ────────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS draft_pairings (
        id                  SERIAL PRIMARY KEY,
        round_id            INTEGER NOT NULL REFERENCES draft_rounds(id) ON DELETE CASCADE,
        player1_user_id     INTEGER REFERENCES users(id),
        player2_user_id     INTEGER REFERENCES users(id),
        player1_deck_id     INTEGER REFERENCES user_decks(id),
        player2_deck_id     INTEGER REFERENCES user_decks(id),
        player1_wins        INTEGER NOT NULL DEFAULT 0,
        player2_wins        INTEGER NOT NULL DEFAULT 0,
        winner_user_id      INTEGER REFERENCES users(id),
        player1_confirmed   VARCHAR(5) NOT NULL DEFAULT 'no',
        player2_confirmed   VARCHAR(5) NOT NULL DEFAULT 'no',
        status              VARCHAR(20) NOT NULL DEFAULT 'pending',
        created_at          TIMESTAMP NOT NULL DEFAULT NOW()
    );
    """,
    # ── Round feedback ────────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS round_feedback (
        id                  SERIAL PRIMARY KEY,
        pairing_id          INTEGER NOT NULL REFERENCES draft_pairings(id) ON DELETE CASCADE,
        user_id             INTEGER NOT NULL REFERENCES users(id),
        liked_card_ids      TEXT,
        disliked_card_ids   TEXT,
        liked_notes         TEXT,
        disliked_notes      TEXT,
        general_thoughts    TEXT,
        created_at          TIMESTAMP NOT NULL DEFAULT NOW()
    );
    """,
    # ── Post-draft feedback ───────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS post_draft_feedback (
        id                          SERIAL PRIMARY KEY,
        draft_event_id              INTEGER NOT NULL REFERENCES draft_events(id) ON DELETE CASCADE,
        user_id                     INTEGER NOT NULL REFERENCES users(id),
        overall_rating              INTEGER,
        overall_thoughts            TEXT,
        standout_card_ids           TEXT,
        underperformer_card_ids     TEXT,
        recommendations_for_owner   TEXT,
        created_at                  TIMESTAMP NOT NULL DEFAULT NOW()
    );
    """,
]

try:
    with engine.connect() as conn:
        for sql in MIGRATIONS:
            conn.execute(text(sql))
        conn.commit()
    print("✓ Migration completed successfully!")
    print("  — cubes: life_total, pack_count, pack_size, draft_rules, gameplay_rules")
    print("  — draft_events: event_type, num_rounds, best_of, current_round")
    print("  — New tables: draft_seats, draft_rounds, draft_pairings, round_feedback, post_draft_feedback")
except Exception as e:
    print(f"ERROR: {e}")
    exit(1)
