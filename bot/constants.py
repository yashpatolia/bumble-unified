DUNGEON_XP_TABLE = {0: 0, 1: 50, 2: 125, 3: 235, 4: 395, 5: 625, 6: 955, 7: 1425, 8: 2095, 9: 3045, 10: 4385, 11: 6275,
                    12: 8940, 13: 12700, 14: 17960, 15: 25340, 16: 35640, 17: 50040, 18: 70040, 19: 97640, 20: 135640,
                    21: 188140, 22: 259640, 23: 356640, 24: 488640, 25: 668640, 26: 911640, 27: 1239640, 28: 1684640,
                    29: 2284640, 30: 3084640, 31: 4149640, 32: 5559640, 33: 7459640, 34: 9959640, 35: 13259640,
                    36: 17559640, 37: 23159640, 38: 30359640, 39: 39559640, 40: 51559640, 41: 66559640, 42: 85559640,
                    43: 109559640, 44: 139559640, 45: 177559640, 46: 225559640, 47: 285559640, 48: 360559640,
                    49: 453559640, 50: 569809640, 51: 769809640}

DUNGEON_INDIVIDUAL_XP_TABLE = {0: 0, 1: 50, 2: 75, 3: 110, 4: 160, 5: 230, 6: 330, 7: 470, 8: 670, 9: 950, 10: 1340,
                               11: 1890, 12: 2665, 13: 3760, 14: 5260, 15: 7380, 16: 10300, 17: 14400, 18: 20000,
                               19: 27600, 20: 38000, 21: 52500, 22: 71500, 23: 97000, 24: 132000, 25: 180000,
                               26: 243000, 27: 328000, 28: 445000, 29: 600000, 30: 800000, 31: 1065000, 32: 1410000,
                               33: 1900000, 34: 2500000, 35: 3300000, 36: 4300000, 37: 5600000, 38: 7200000,
                               39: 9200000, 40: 12000000, 41: 15000000, 42: 19000000, 43: 24000000, 44: 30000000,
                               45: 38000000, 46: 48000000, 47: 60000000, 48: 75000000, 49: 93000000,
                               50: 116250000, 51: 200000000}

MP_VALUES = {
    "UNCOMMON": 5,
    "COMMON": 3,
    "RARE": 8,
    "EPIC": 12,
    "LEGENDARY": 16,
    "MYTHIC": 22,
}

GAMEMODE = {
    "": "",
    "ironman": " ♻",
    "bingo": " Ⓑ",
    "island": " 🏝"
}


# Base XP value of each dungeon floor, used to project XP earned per run.
DUNGEON_FLOOR_XP = {
    "entrance": 55, "f1": 110, "f2": 220, "f3": 560, "f4": 1420, "f5": 2400, "f6": 4880, "f7": 28000,
    "m1": 15000, "m2": 20000, "m3": 35000, "m4": 55000, "m5": 70000, "m6": 100000, "m7": 300000,
}

# Order matters: class average maths iterates these in the same order as the reference calculator,
# which resolves "highest remaining XP" ties in favour of the first class listed.
DUNGEON_CLASSES = ("archer", "berserk", "healer", "mage", "tank")

DUNGEON_CLASS_DISPLAY = {
    "archer": "Arch", "berserk": "Bers", "healer": "Heal", "mage": "Mage", "tank": "Tank",
}

# Single-letter shorthand for .rtcaf's skip-class arguments.
DUNGEON_CLASS_LETTERS = {"a": "archer", "b": "berserk", "h": "healer", "m": "mage", "t": "tank"}

# Essence shop perks that boost a single dungeon class's XP gain, 2% per level up to V.
CLASS_PERK_KEYS = {
    "archer": "toxophilite",
    "berserk": "unbridled_rage",
    "healer": "heart_of_gold",
    "mage": "cold_efficiency",
    "tank": "diamond_in_the_rough",
}
CLASS_PERK_PER_LEVEL = 0.02
CLASS_PERK_MAX = 0.10

# Hecatomb (boots enchantment) starts at 0.56% and gains 0.16% per level, capping at 2% for level X.
HECATOMB_BASE = 0.0056
HECATOMB_PER_LEVEL = 0.0016
HECATOMB_MAX = 0.02

# Scarf accessory line — only the highest tier owned applies.
SCARF_ACCESSORY_BOOSTS = {
    "SCARF_STUDIES": 0.02,
    "SCARF_THESIS": 0.04,
    "SCARF_GRIMOIRE": 0.06,
}
SCARF_ACCESSORY_MAX = 0.06

# Catacombs Graduate attribute shard, 2% per level up to X.
CATA_GRADUATE_PER_LEVEL = 0.02
CATA_GRADUATE_MAX = 0.20

# Hypixel stores attribute progress as a raw shard count, not a level. Cumulative shards
# needed for levels I..X, which differ by the shard's rarity.
ATTRIBUTE_LEVEL_THRESHOLDS = {
    "common":    (1, 4, 9, 15, 22, 30, 40, 54, 72, 96),
    "uncommon":  (1, 3, 6, 10, 15, 21, 28, 36, 48, 64),
    "rare":      (1, 3, 6, 9, 13, 17, 22, 28, 36, 48),
    "epic":      (1, 2, 4, 6, 9, 12, 16, 20, 25, 32),
    "legendary": (1, 2, 3, 5, 7, 9, 12, 15, 19, 24),
}

# Rarity of the Scarf shard that syphons into Catacombs Graduate. Inferred, not confirmed:
# a maxed test account showed exactly 32 shards, which is the Epic level X threshold and no
# other rarity's. If that turns out wrong, correcting this one value fixes the boost.
CATA_GRADUATE_SHARD_RARITY = "epic"

# Mayors that boost dungeon XP. Anything else is a 1.0 multiplier.
MAYOR_XP_MULTIPLIERS = {"derpy": 1.5, "aura": 1.59}
