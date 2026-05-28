-- One Discord account should map to exactly one Minecraft UUID.
-- Some users linked twice (e.g. after an IGN change), leaving duplicate discord_id rows.
-- Keep the link on the UUID that is currently in guild_members; clear the others.

UPDATE users u
SET discord_id = NULL, discord_name = NULL
WHERE u.discord_id IS NOT NULL
  -- this row's UUID is NOT in guild_members ...
  AND NOT EXISTS (
      SELECT 1 FROM guild_members gm WHERE gm.uuid = u.uuid
  )
  -- ... but another row with the same discord_id IS in guild_members
  AND EXISTS (
      SELECT 1 FROM users u2
      WHERE u2.discord_id = u.discord_id
        AND u2.uuid != u.uuid
        AND EXISTS (SELECT 1 FROM guild_members gm WHERE gm.uuid = u2.uuid)
  );

-- Enforce uniqueness going forward (NULL discord_id rows are excluded)
CREATE UNIQUE INDEX IF NOT EXISTS users_discord_id_unique
    ON users (discord_id)
    WHERE discord_id IS NOT NULL;
