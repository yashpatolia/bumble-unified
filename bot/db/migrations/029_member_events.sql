-- Roster history for the member page: when someone joined, left or was kicked, was promoted or
-- demoted, or changed their Minecraft name. `uuid` is the stable key (it survives renames and
-- moves between guilds); it is NULL only when the player was not yet resolved.
CREATE TABLE IF NOT EXISTS member_events (
    id          BIGSERIAL PRIMARY KEY,
    guild_key   TEXT NOT NULL,
    uuid        TEXT,
    ign         TEXT NOT NULL,
    kind        TEXT NOT NULL,                     -- joined | left | kicked | promoted | demoted | renamed
    detail      JSONB NOT NULL DEFAULT '{}'::jsonb, -- {"from": ..., "to": ...} for ranks and names
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS member_events_uuid ON member_events (uuid, occurred_at DESC);
CREATE INDEX IF NOT EXISTS member_events_ign ON member_events (guild_key, LOWER(ign), occurred_at DESC);
