-- Active guild mutes, so the Discord timeout can be kept in step (and lifted on time) even if the
-- bot was offline when a mute ran out or was lifted. `expires_at` is the real end of the mute.
CREATE TABLE IF NOT EXISTS guild_mutes (
    guild_key  TEXT NOT NULL,
    ign        CITEXT NOT NULL,
    muted_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (guild_key, ign)
);
