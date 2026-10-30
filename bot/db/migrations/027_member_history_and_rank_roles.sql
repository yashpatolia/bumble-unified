-- Daily snapshots also keep Catacombs XP and per-boss slayer XP (read from the same profiles
-- response the level comes from), for the member page's history charts.
ALTER TABLE guild_member_level_history ADD COLUMN IF NOT EXISTS catacombs_xp DOUBLE PRECISION;
ALTER TABLE guild_member_level_history ADD COLUMN IF NOT EXISTS slayer_xp JSONB;

-- Discord role handed out for each guild rank, {bot_rank_key: role_id}. Empty means no sync.
ALTER TABLE guild_config ADD COLUMN IF NOT EXISTS rank_roles JSONB NOT NULL DEFAULT '{}'::jsonb;
