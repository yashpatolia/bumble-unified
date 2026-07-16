UPDATE dyes SET weight = 1.666667e-04 WHERE dye_id IN ('iceberg_dye', 'midnight_dye', 'secret_dye');
UPDATE dyes SET weight = 1.499999e-04 WHERE dye_id = 'bone_dye';
UPDATE dyes SET weight = 1.333333e-04 WHERE dye_id IN ('carmine_dye', 'emerald_dye');
UPDATE dyes SET weight = 1.0e-04 WHERE dye_id IN (
    'brick_red_dye', 'byzantium_dye', 'celeste_dye', 'cyclamen_dye',
    'flame_dye', 'mango_dye', 'matcha_dye', 'pearlescent_dye'
);
UPDATE dyes SET weight = 6.666667e-05 WHERE dye_id = 'mocha_dye';
UPDATE dyes SET weight = 5.0e-05 WHERE dye_id = 'wild_strawberry_dye';
