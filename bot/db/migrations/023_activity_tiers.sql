ALTER TABLE guild_config ADD COLUMN IF NOT EXISTS activity_tiers JSONB NOT NULL DEFAULT '{}'::jsonb;
