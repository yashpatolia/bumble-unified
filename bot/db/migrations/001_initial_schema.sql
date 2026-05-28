CREATE TABLE IF NOT EXISTS users (
    uuid         TEXT PRIMARY KEY,
    ign          TEXT,
    discord_id   BIGINT,
    discord_name TEXT
);

CREATE TABLE IF NOT EXISTS dyes (
    dye_id   TEXT PRIMARY KEY,
    dye_name TEXT,
    weight   DOUBLE PRECISION,
    hex      TEXT
);

CREATE TABLE IF NOT EXISTS users_dyes (
    uuid     TEXT REFERENCES users(uuid),
    dye_id   TEXT REFERENCES dyes(dye_id),
    received SMALLINT DEFAULT 0
);
