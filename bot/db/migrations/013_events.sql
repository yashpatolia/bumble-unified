-- Add can_manage_events permission to panel users
ALTER TABLE panel_users ADD COLUMN IF NOT EXISTS can_manage_events BOOLEAN NOT NULL DEFAULT FALSE;

-- Top-level events table (supports bingo and future event types)
CREATE TABLE IF NOT EXISTS events (
    id         SERIAL PRIMARY KEY,
    slug       TEXT NOT NULL UNIQUE,
    type       TEXT NOT NULL DEFAULT 'bingo',
    name       TEXT NOT NULL,
    -- individual, team, combined_shared, combined_versus, combined_individual
    mode       TEXT NOT NULL DEFAULT 'individual',
    guilds     TEXT[] NOT NULL,            -- e.g. '{bk}', '{bu}', '{bk,bu}'
    status     TEXT NOT NULL DEFAULT 'draft',  -- draft | active | ended
    starts_at  TIMESTAMPTZ,
    ends_at    TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5x5 bingo task grid (positions 0-24; position 12 = free space)
CREATE TABLE IF NOT EXISTS bingo_tasks (
    id          SERIAL PRIMARY KEY,
    event_id    INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    position    INTEGER NOT NULL CHECK (position >= 0 AND position <= 24),
    name        TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    -- skill_xp | slayer_tier | dungeon_xp | collection | free
    task_type   TEXT NOT NULL,
    -- {"skill":"farming","amount":1000000}
    -- {"boss":"zombie","tier":4,"amount":10}
    -- {"dungeon":"catacombs","amount":500000}
    -- {"item":"WHEAT","amount":50000}
    target      JSONB NOT NULL DEFAULT '{}',
    difficulty  TEXT NOT NULL DEFAULT 'medium',  -- easy | medium | hard
    UNIQUE (event_id, position)
);

-- Per-player progress on each bingo task (baseline = value at event start)
CREATE TABLE IF NOT EXISTS bingo_progress (
    id           SERIAL PRIMARY KEY,
    event_id     INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    uuid         TEXT NOT NULL,
    task_id      INTEGER NOT NULL REFERENCES bingo_tasks(id) ON DELETE CASCADE,
    baseline     DOUBLE PRECISION NOT NULL DEFAULT 0,
    current_val  DOUBLE PRECISION NOT NULL DEFAULT 0,
    completed    BOOLEAN NOT NULL DEFAULT FALSE,
    completed_at TIMESTAMPTZ,
    last_updated TIMESTAMPTZ,
    UNIQUE (event_id, uuid, task_id)
);

CREATE INDEX IF NOT EXISTS bingo_progress_event_uuid ON bingo_progress (event_id, uuid);
