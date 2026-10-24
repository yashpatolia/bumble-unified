ALTER TABLE panel_users ADD COLUMN IF NOT EXISTS can_manage_config BOOLEAN NOT NULL DEFAULT FALSE;

-- Per-guild settings edited from the panel. Empty JSON means "use the built-in defaults".
CREATE TABLE IF NOT EXISTS guild_config (
    guild_key         TEXT PRIMARY KEY,
    rank_requirements JSONB NOT NULL DEFAULT '{}'::jsonb,
    attention         JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_by        TEXT,
    updated_at        TIMESTAMPTZ
);
