-- Members an officer has excused (vacation, alt, etc.). Excused members are left out of the
-- inactivity warnings. `until_date` NULL means excused until someone removes it.
CREATE TABLE IF NOT EXISTS excused_members (
    guild_key  TEXT   NOT NULL,
    ign        CITEXT NOT NULL,
    reason     TEXT,
    until_date DATE,
    created_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (guild_key, ign)
);
