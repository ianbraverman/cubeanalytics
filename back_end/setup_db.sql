-- Cube Foundry — production schema
-- Run inside Cloud Shell: \i setup_db.sql
-- Database cube_foundry must already exist (created via GCP Console in Phase 5)

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR NOT NULL UNIQUE,
    email VARCHAR NOT NULL UNIQUE,
    hashed_password VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_users_username ON users (username);
CREATE INDEX IF NOT EXISTS ix_users_email ON users (email);

CREATE TABLE IF NOT EXISTS cards (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL UNIQUE,
    scryfall_id VARCHAR NOT NULL UNIQUE,
    mana_cost VARCHAR,
    type_line VARCHAR,
    colors JSON,
    cmc FLOAT,
    power VARCHAR,
    toughness VARCHAR,
    oracle_text TEXT,
    image_url VARCHAR,
    small_image_url VARCHAR,
    rarity VARCHAR,
    set_code VARCHAR,
    set_name VARCHAR,
    scryfall_uri VARCHAR,
    cached_data TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_cards_name ON cards (name);
CREATE INDEX IF NOT EXISTS ix_cards_scryfall_id ON cards (scryfall_id);

CREATE TABLE IF NOT EXISTS cubes (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    description TEXT,
    owner_id INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    life_total INTEGER NOT NULL DEFAULT 20,
    pack_count INTEGER NOT NULL DEFAULT 3,
    pack_size INTEGER NOT NULL DEFAULT 15,
    draft_rules TEXT,
    gameplay_rules TEXT
);
CREATE INDEX IF NOT EXISTS ix_cubes_name ON cubes (name);

CREATE TABLE IF NOT EXISTS draft_events (
    id SERIAL PRIMARY KEY,
    cube_id INTEGER NOT NULL REFERENCES cubes(id),
    password_hash VARCHAR NOT NULL,
    name VARCHAR(200),
    status VARCHAR(30) DEFAULT 'active',
    num_players INTEGER DEFAULT 0,
    ai_summary TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    event_type VARCHAR(20) DEFAULT 'casual',
    num_rounds INTEGER,
    best_of INTEGER DEFAULT 1,
    current_round INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS cube_cards (
    id SERIAL PRIMARY KEY,
    cube_id INTEGER NOT NULL REFERENCES cubes(id),
    card_id INTEGER NOT NULL REFERENCES cards(id),
    quantity INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    removed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_decks (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    draft_event_id INTEGER NOT NULL REFERENCES draft_events(id),
    player_name VARCHAR(100),
    deck_name VARCHAR(200),
    deck_cards TEXT NOT NULL,
    sideboard_cards TEXT,
    full_pool_cards TEXT,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    record VARCHAR,
    deck_photo_url VARCHAR(500),
    pool_photo_url VARCHAR(500),
    ai_description TEXT,
    archetype VARCHAR(30),
    archetype_detail VARCHAR(100),
    color_identity VARCHAR(10),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS draft_participants (
    id SERIAL PRIMARY KEY,
    draft_event_id INTEGER NOT NULL REFERENCES draft_events(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    joined_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS draft_seats (
    id SERIAL PRIMARY KEY,
    draft_event_id INTEGER NOT NULL REFERENCES draft_events(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    seat_number INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS draft_rounds (
    id SERIAL PRIMARY KEY,
    draft_event_id INTEGER NOT NULL REFERENCES draft_events(id),
    round_number INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS draft_pairings (
    id SERIAL PRIMARY KEY,
    round_id INTEGER NOT NULL REFERENCES draft_rounds(id),
    player1_user_id INTEGER REFERENCES users(id),
    player2_user_id INTEGER REFERENCES users(id),
    player1_deck_id INTEGER REFERENCES user_decks(id),
    player2_deck_id INTEGER REFERENCES user_decks(id),
    player1_wins INTEGER DEFAULT 0,
    player2_wins INTEGER DEFAULT 0,
    winner_user_id INTEGER REFERENCES users(id),
    player1_confirmed VARCHAR(5) DEFAULT 'no',
    player2_confirmed VARCHAR(5) DEFAULT 'no',
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS feedback (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    draft_event_id INTEGER NOT NULL REFERENCES draft_events(id),
    rating INTEGER NOT NULL,
    comment TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS card_feedback (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    card_id INTEGER NOT NULL REFERENCES cards(id),
    draft_event_id INTEGER REFERENCES draft_events(id),
    feedback_type VARCHAR NOT NULL,
    rating INTEGER NOT NULL,
    comment TEXT NOT NULL,
    vector_id VARCHAR,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS post_draft_feedback (
    id SERIAL PRIMARY KEY,
    draft_event_id INTEGER NOT NULL REFERENCES draft_events(id),
    user_id INTEGER REFERENCES users(id),
    player_name VARCHAR,
    overall_rating INTEGER,
    overall_thoughts TEXT,
    standout_card_ids TEXT,
    underperformer_card_ids TEXT,
    recommendations_for_owner TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
