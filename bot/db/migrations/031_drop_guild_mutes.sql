-- The Discord timeout mirroring of guild mutes was removed; drop its table.
DROP TABLE IF EXISTS guild_mutes;
