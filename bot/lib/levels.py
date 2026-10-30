"""Level maths shared by the player classes and the panel (kept free of heavy imports)."""
from constants import DUNGEON_XP_TABLE, DUNGEON_INDIVIDUAL_XP_TABLE


def catacombs_level(cata_xp: float) -> float:
    """Catacombs level (with the fraction towards the next) for a raw XP total."""
    level = [k for k, v in DUNGEON_XP_TABLE.items() if cata_xp >= v][-1]
    if level >= 50:
        return 50 + round((cata_xp - DUNGEON_XP_TABLE[50]) / 200_000_000, 2)
    return level + round((cata_xp - DUNGEON_XP_TABLE[level]) / DUNGEON_INDIVIDUAL_XP_TABLE[level + 1], 2)
