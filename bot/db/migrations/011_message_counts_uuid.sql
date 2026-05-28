-- Add uuid to message_counts and switch the unique constraint to UUID-based.
-- This fixes duplicate rows caused by the same player chatting with different IGN casing.

ALTER TABLE message_counts ADD COLUMN IF NOT EXISTS uuid TEXT;

-- Populate UUID and fix IGN casing using guild_members as the source of truth
-- (guild_members.ign is citext so the match is case-insensitive)
UPDATE message_counts mc
SET
    uuid = gm.uuid,
    ign  = gm.ign::TEXT
FROM guild_members gm
WHERE gm.guild_key   = mc.guild_key
  AND gm.ign         = mc.ign       -- citext = TEXT comparison, case-insensitive
  AND gm.uuid IS NOT NULL
  AND gm.uuid != '';

-- Merge duplicate rows that now share the same (guild_key, uuid, period_type, period_key)
-- First: update the survivor row with the combined count
UPDATE message_counts mc
SET count = agg.total_count
FROM (
    SELECT MIN(ctid) AS keep_ctid, SUM(count) AS total_count
    FROM message_counts
    WHERE uuid IS NOT NULL AND uuid != ''
    GROUP BY guild_key, uuid, period_type, period_key
    HAVING COUNT(*) > 1
) agg
WHERE mc.ctid = agg.keep_ctid;

-- Then: delete the extra duplicate rows
DELETE FROM message_counts
WHERE uuid IS NOT NULL AND uuid != ''
  AND ctid NOT IN (
      SELECT MIN(ctid)
      FROM message_counts
      WHERE uuid IS NOT NULL AND uuid != ''
      GROUP BY guild_key, uuid, period_type, period_key
  );

-- Drop the old case-sensitive IGN-based unique constraint
ALTER TABLE message_counts
    DROP CONSTRAINT IF EXISTS message_counts_guild_key_ign_period_type_period_key_key;

-- Add a new UUID-based unique index (partial — only applies to rows that have a UUID)
CREATE UNIQUE INDEX IF NOT EXISTS message_counts_uuid_unique
    ON message_counts (guild_key, uuid, period_type, period_key)
    WHERE uuid IS NOT NULL AND uuid != '';
