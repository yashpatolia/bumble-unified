-- Enable case-insensitive text extension
CREATE EXTENSION IF NOT EXISTS citext;

-- Remove duplicate guild_members rows, keeping the properly-cased (non-all-lowercase) version
WITH ranked AS (
    SELECT ctid,
           ROW_NUMBER() OVER (
               PARTITION BY guild_key, LOWER(ign)
               ORDER BY
                 stats_fetched_at DESC NULLS LAST,
                 (LENGTH(ign) - LENGTH(LOWER(ign))) DESC
           ) AS rn
    FROM guild_members
)
DELETE FROM guild_members WHERE ctid IN (SELECT ctid FROM ranked WHERE rn > 1);

-- Switch ign to citext so the PK is case-insensitive going forward
ALTER TABLE guild_members DROP CONSTRAINT guild_members_pkey;
ALTER TABLE guild_members ALTER COLUMN ign TYPE citext;
ALTER TABLE guild_members ADD PRIMARY KEY (guild_key, ign);
