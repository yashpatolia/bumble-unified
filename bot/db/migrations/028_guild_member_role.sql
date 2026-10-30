-- Discord role that marks someone as being in the guild at all, handed out next to their rank role.
-- Empty means look for a role named like the guild ("Bumble University").
ALTER TABLE guild_config ADD COLUMN IF NOT EXISTS member_role BIGINT;
