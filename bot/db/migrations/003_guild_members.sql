CREATE TABLE IF NOT EXISTS guild_members (
    guild_key        TEXT NOT NULL,
    ign              TEXT NOT NULL,
    uuid             TEXT,
    rank             TEXT NOT NULL DEFAULT '',
    skyblock_level   DOUBLE PRECISION,
    last_login       BIGINT,
    stats_fetched_at BIGINT,
    PRIMARY KEY (guild_key, ign)
);
