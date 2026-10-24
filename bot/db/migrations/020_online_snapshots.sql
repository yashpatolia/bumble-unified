CREATE TABLE IF NOT EXISTS online_snapshots (
    guild_key    TEXT NOT NULL,
    taken_at     TIMESTAMPTZ NOT NULL,
    online_count INTEGER NOT NULL,
    PRIMARY KEY (guild_key, taken_at)
);
