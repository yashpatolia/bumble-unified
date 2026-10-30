-- Wrong ids carried over from the old DYE_ROLES/DYE_EMOJIS constants (seeded by 025): two emoji
-- ids with mistyped digits, and emerald_dye sharing celadon_dye's role. Each statement only
-- touches a row still holding the wrong value, so a fix made on the panel is left alone.
UPDATE dyes SET emoji_id = 1303236474761908265 WHERE dye_id = 'aquamarine_dye' AND emoji_id = 1303264474761908265;
UPDATE dyes SET emoji_id = 1303253635060469781 WHERE dye_id = 'nyanza_dye' AND emoji_id = 1303253635064697811;
UPDATE dyes SET role_id = 1355738942787420322 WHERE dye_id = 'emerald_dye' AND role_id = 1355738940262318251;
