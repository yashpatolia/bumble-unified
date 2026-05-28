CREATE TABLE IF NOT EXISTS message_counts (
    guild_key   TEXT NOT NULL,
    ign         TEXT NOT NULL,
    period_type TEXT NOT NULL,  -- 'lifetime', 'month', 'week'
    period_key  TEXT NOT NULL,  -- '' for lifetime, '2025-05' for month, '2025-W21' for week
    count       BIGINT NOT NULL DEFAULT 0,
    UNIQUE (guild_key, ign, period_type, period_key)
);
