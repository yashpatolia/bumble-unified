ALTER TABLE users_dyes
    ALTER COLUMN received DROP DEFAULT;
ALTER TABLE users_dyes
    ALTER COLUMN received TYPE BOOLEAN USING (received <> 0);
ALTER TABLE users_dyes
    ALTER COLUMN received SET DEFAULT FALSE;

ALTER TABLE users_dyes
    ADD CONSTRAINT users_dyes_uuid_dye_id_key UNIQUE (uuid, dye_id);

INSERT INTO dyes (dye_id, dye_name, weight, hex) VALUES
    ('carmine_dye', 'Carmine Dye', 1.333333e-04, '960018'),
    ('archfiend_dye', 'Archfiend Dye', 0.015, 'B80036'),
    ('sangria_dye', 'Sangria Dye', 0.001, 'D40808'),
    ('necron_dye', 'Necron Dye', 0.04, 'E7413C'),
    ('brick_red_dye', 'Brick Red Dye', 1.0e-04, 'CB4154'),
    ('flame_dye', 'Flame Dye', 1.0e-04, 'E25822'),
    ('copper_dye', 'Copper Dye', 0.001, 'B87333'),
    ('fossil_dye', 'Fossil Dye', 0.0002, '866F12'),
    ('mango_dye', 'Mango Dye', 1.0e-04, 'FDBE02'),
    ('nyanza_dye', 'Nyanza Dye', 0.0004, 'E9FFDB'),
    ('emerald_dye', 'Emerald Dye', 1.333333e-04, '50C878'),
    ('jade_dye', 'Jade Dye', 0.0002, '00A86B'),
    ('matcha_dye', 'Matcha Dye', 1.0e-04, '74A12E'),
    ('holly_dye', 'Holly Dye', 0.0125, '3C6746'),
    ('celeste_dye', 'Celeste Dye', 1.0e-04, 'B2FFFF'),
    ('frostbitten_dye', 'Frostbitten Dye', 0.0004, '09D8EB'),
    ('iceberg_dye', 'Iceberg Dye', 1.666667e-04, '71A6D2'),
    ('tentacle_dye', 'Tentacle Dye', 0.001, '324D6C'),
    ('pearlescent_dye', 'Pearlescent Dye', 1.0e-04, '115555'),
    ('midnight_dye', 'Midnight Dye', 1.666667e-04, '50216C'),
    ('dark_purple_dye', 'Dark Purple Dye', 0.25, '301934'),
    ('byzantium_dye', 'Byzantium Dye', 1.0e-04, '702963'),
    ('wild_strawberry_dye', 'Wild Strawberry Dye', 5.0e-05, 'FF43A4'),
    ('cyclamen_dye', 'Cyclamen Dye', 1.0e-04, 'F56FA1'),
    ('nadeshiko_dye', 'Nadeshiko Dye', 0.0013, 'F6ADC6'),
    ('pelt_dye', 'Pelt Dye', 0.0004, '50414C'),
    ('secret_dye', 'Secret Dye', 1.666667e-04, '7D7D7D'),
    ('periwinkle_dye', 'Periwinkle Dye', 0.0002, 'CCCCFF'),
    ('bone_dye', 'Bone Dye', 1.499999e-04, 'E3DAC9'),
    ('livid_dye', 'Livid Dye', 0.02, 'CEB7AA'),
    ('mocha_dye', 'Mocha Dye', 6.666667e-05, '967969'),
    ('dung_dye', 'Dung Dye', 0.0004, '4F2A2A'),
    ('aquamarine_dye', 'Aquamarine Dye', 0.001, '7FFFD4'),
    ('celadon_dye', 'Celadon Dye', 0.01, 'ACE1AF')
ON CONFLICT (dye_id) DO NOTHING;
