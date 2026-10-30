-- Settings that used to be hard coded, now edited on the panel's Config page.

-- Shared (not per-guild) settings: one JSON value per key, e.g. 'warpout', 'censor'.
-- A missing key means "use the built-in defaults" (lib/shared_settings.py).
CREATE TABLE IF NOT EXISTS bot_settings (
    key         TEXT PRIMARY KEY,
    value       JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_by  TEXT,
    updated_at  TIMESTAMPTZ
);

-- Per-guild Minecraft version for the bridge bot; NULL means MINECRAFT_VERSION from .env.
ALTER TABLE guild_config ADD COLUMN IF NOT EXISTS minecraft_version TEXT;

-- Each dye's Discord colour role and emoji, previously DYE_ROLES/DYE_EMOJIS in constants.py.
ALTER TABLE dyes ADD COLUMN IF NOT EXISTS role_id BIGINT;
ALTER TABLE dyes ADD COLUMN IF NOT EXISTS emoji_id BIGINT;

UPDATE dyes SET role_id = 1355740549755437056, emoji_id = 1303264474761908265 WHERE dye_id = 'aquamarine_dye';
UPDATE dyes SET role_id = 1355641868670599390, emoji_id = 1303804446467424347 WHERE dye_id = 'archfiend_dye';
UPDATE dyes SET role_id = 1355743187964006551, emoji_id = 1303252064578703421 WHERE dye_id = 'bone_dye';
UPDATE dyes SET role_id = 1355738926282838297, emoji_id = 1303252073340604426 WHERE dye_id = 'brick_red_dye';
UPDATE dyes SET role_id = 1355740569347031251, emoji_id = 1303252099798401035 WHERE dye_id = 'byzantium_dye';
UPDATE dyes SET role_id = 1355526901787263149, emoji_id = 1303252109340446774 WHERE dye_id = 'carmine_dye';
UPDATE dyes SET role_id = 1355738940262318251, emoji_id = 1303252121193283645 WHERE dye_id = 'celadon_dye';
UPDATE dyes SET role_id = 1355740550116151407, emoji_id = 1303252130681061376 WHERE dye_id = 'celeste_dye';
UPDATE dyes SET role_id = 1355738931391500379, emoji_id = 1303252138373283911 WHERE dye_id = 'copper_dye';
UPDATE dyes SET role_id = 1355740573121908818, emoji_id = 1303252146501845012 WHERE dye_id = 'cyclamen_dye';
UPDATE dyes SET role_id = 1355740566532391113, emoji_id = 1303252452232925184 WHERE dye_id = 'dark_purple_dye';
UPDATE dyes SET role_id = 1355743199372771368, emoji_id = 1303252461611515946 WHERE dye_id = 'dung_dye';
UPDATE dyes SET role_id = 1355738940262318251, emoji_id = 1303252473645109268 WHERE dye_id = 'emerald_dye';
UPDATE dyes SET role_id = 1355738929088696350, emoji_id = 1303252490661400606 WHERE dye_id = 'flame_dye';
UPDATE dyes SET role_id = 1355738933228605488, emoji_id = 1303253332500156457 WHERE dye_id = 'fossil_dye';
UPDATE dyes SET role_id = 1355740551466450975, emoji_id = 1303253342625075281 WHERE dye_id = 'frostbitten_dye';
UPDATE dyes SET role_id = 1355740546546536489, emoji_id = 1303253356642566164 WHERE dye_id = 'holly_dye';
UPDATE dyes SET role_id = 1355814461549580349, emoji_id = 1303253370533838858 WHERE dye_id = 'iceberg_dye';
UPDATE dyes SET role_id = 1355738952148975658, emoji_id = 1303253382269632542 WHERE dye_id = 'jade_dye';
UPDATE dyes SET role_id = 1355743189587197952, emoji_id = 1303253397486440468 WHERE dye_id = 'livid_dye';
UPDATE dyes SET role_id = 1355738935778742462, emoji_id = 1303253410585514055 WHERE dye_id = 'mango_dye';
UPDATE dyes SET role_id = 1355738954044932216, emoji_id = 1303253543905529867 WHERE dye_id = 'matcha_dye';
UPDATE dyes SET role_id = 1355740553580515400, emoji_id = 1303253556593164361 WHERE dye_id = 'midnight_dye';
UPDATE dyes SET role_id = 1355743195065221252, emoji_id = 1303253570510127184 WHERE dye_id = 'mocha_dye';
UPDATE dyes SET role_id = 1355740602725040319, emoji_id = 1303253584325906462 WHERE dye_id = 'nadeshiko_dye';
UPDATE dyes SET role_id = 1355738922478600252, emoji_id = 1303253598599254056 WHERE dye_id = 'necron_dye';
UPDATE dyes SET role_id = 1355738938127683664, emoji_id = 1303253635064697811 WHERE dye_id = 'nyanza_dye';
UPDATE dyes SET role_id = 1355740552678867036, emoji_id = 1303253656287711294 WHERE dye_id = 'pearlescent_dye';
UPDATE dyes SET role_id = 1355740604352430150, emoji_id = 1303253986396078080 WHERE dye_id = 'pelt_dye';
UPDATE dyes SET role_id = 1355740605736681492, emoji_id = 1303254002280169504 WHERE dye_id = 'periwinkle_dye';
UPDATE dyes SET role_id = 1355738519644930058, emoji_id = 1303254012845621338 WHERE dye_id = 'sangria_dye';
UPDATE dyes SET role_id = 1355743191617245184, emoji_id = 1303254024790868090 WHERE dye_id = 'secret_dye';
UPDATE dyes SET role_id = 1355740551969902773, emoji_id = 1303254036656422932 WHERE dye_id = 'tentacle_dye';
UPDATE dyes SET role_id = 1355740570697338972, emoji_id = 1303254046668361769 WHERE dye_id = 'wild_strawberry_dye';
