import re
from lib import deep_get

# Cumulative kills required to reach each tier (index 0 = tier 1 ... index 24 = tier 25)
# Outer index = bracket number - 1 (0-based)
_BRACKETS = [
    # Bracket 1
    [20, 40, 60, 100, 200, 400, 800, 1400, 2000, 3000,
     6000, 12000, 20000, 30000, 40000, 50000, 60000, 72000, 86000, 100000,
     200000, 400000, 600000, 800000, 1000000],
    # Bracket 2
    [5, 10, 15, 25, 50, 100, 200, 350, 500, 750,
     1500, 3000, 5000, 7500, 10000, 12500, 15000, 18000, 21500, 25000,
     50000, 100000, 150000, 200000, 250000],
    # Bracket 3
    [4, 8, 12, 16, 20, 40, 80, 140, 200, 300,
     600, 1200, 2000, 3000, 4000, 5000, 6000, 7200, 8600, 10000,
     20000, 40000, 60000, 80000, 100000],
    # Bracket 4
    [2, 4, 6, 10, 15, 20, 25, 35, 50, 75,
     150, 300, 500, 750, 1000, 1350, 1650, 2000, 2500, 3000,
     5000, 10000, 15000, 20000, 25000],
    # Bracket 5
    [1, 2, 3, 5, 7, 10, 15, 20, 25, 30,
     60, 120, 200, 300, 400, 500, 600, 720, 860, 1000,
     2000, 4000, 6000, 8000, 10000],
    # Bracket 6
    [1, 2, 3, 5, 7, 9, 14, 17, 21, 25,
     50, 80, 125, 175, 250, 325, 425, 525, 625, 750,
     1500, 3000, 4500, 6000, 7500],
    # Bracket 7
    [1, 2, 3, 5, 7, 9, 11, 14, 17, 20,
     30, 40, 55, 75, 100, 150, 200, 275, 375, 500,
     1000, 1500, 2000, 2500, 3000],
    # Bracket 8 (tiers 1-10 from wiki; 11-25 extrapolated from pattern)
    [1, 10, 20, 30, 45, 60, 80, 100, 125, 150,
     180, 210, 245, 280, 320, 360, 405, 450, 500, 550,
     650, 800, 1000, 1250, 1550],
]

# Map API family name (kill key with _LEVEL stripped) → bracket index (0-based)
_FAMILY_BRACKET: dict[str, int] = {
    # ── Your Island / Hub ── Bracket 1
    "bat": 0, "creeper": 0, "skeleton": 0, "slime": 0, "spider": 0,
    "witch": 0, "zombie": 0, "wolf": 0, "ruin_wolf": 0,
    "crypt_ghoul": 0, "graveyard_zombie": 0, "unburried_zombie": 0,
    "powder_ghast": 0,
    # Hub ── Bracket 3
    "golden_ghoul": 2, "old_wolf": 2,
    # Hub ── Bracket 4
    "zombie_villager": 3,
    # Hub ── Bracket 5
    "shiny_pig": 4,
    # ── Farming Islands ── Bracket 1
    "chicken": 0, "cow": 0, "mushroom_cow": 0, "pig": 0, "rabbit": 0, "sheep": 0,
    "farming_chicken": 0, "farming_cow": 0, "farming_sheep": 0, "farming_rabbit": 0,
    # ── Deep Caverns ── Bracket 1
    "emerald_slime": 0, "lapis_zombie": 0, "miner_skeleton": 0, "miner_zombie": 0,
    "redstone_pigman": 0, "diamond_zombie": 0, "diamond_skeleton": 0,
    # Deep Caverns ── Bracket 3
    "sneaky_creeper": 2, "invisible_creeper": 2,
    # ── Spider's Den ── Bracket 2
    "dasher_spider": 1, "silverfish": 1, "splitter_spider": 1,
    "voracious_spider": 1, "weaver_spider": 1, "splitter_spider_silverfish": 1,
    # Spider's Den ── Bracket 3
    "flint_skeleton": 2, "spider_jockey": 2,
    # Spider's Den ── Bracket 4
    "arachnes_brood": 3, "rain_slime": 3,
    # Spider's Den ── Bracket 5
    "arachnes_keeper": 4, "brood_mother_spider": 4, "brood_mother": 4,
    # Spider's Den ── Bracket 7
    "arachne": 6,
    # ── The End ── Bracket 3
    "voidling_extremist": 2,
    # The End ── Bracket 4
    "enderman": 3, "voidling_fanatic": 3, "zealot": 3,
    # The End ── Bracket 5
    "endermite": 4, "obsidian_defender": 4, "seer": 4, "obsidian_wither": 4,
    # The End ── Bracket 7
    "end_stone_protector": 6,
    # ── Crimson Isle ── Bracket 2
    "smoldering_blaze": 1,
    # Crimson Isle ── Bracket 3
    "flaming_spider": 2, "flare": 2, "magma_cube": 2, "millennia_aged_blaze": 2,
    "mushroom_bull": 2, "wither_skeleton": 2, "wither_spectre": 2,
    # Crimson Isle ── Bracket 4
    "blaze": 3, "ghast": 3, "kada_knight": 3, "magma_cube_rider": 3,
    # Crimson Isle ── Bracket 5
    "matcho": 4, "tentacle": 4, "vanquisher": 4,
    # Crimson Isle ── Bracket 7
    "ashfang": 6, "barbarian_duke_x": 6, "bladesoul": 6, "mage_outlaw": 6, "magma_boss": 6,
    # ── Dwarven Mines ── Bracket 2
    "ghost": 1, "glacite_walker": 1, "ice_walker": 1, "goblin": 1,
    # Dwarven Mines ── Bracket 4
    "glacite_bowman": 3, "glacite_caver": 3, "glacite_mage": 3, "glacite_mutt": 3,
    "star_sentry": 3, "treasure_hoarder": 3,
    "goblin_knife_thrower": 3, "goblin_weakling_melee": 3, "goblin_weakling_bow": 3,
    "goblin_battler": 3, "goblin_creeper": 3, "goblin_creepertamer": 3, "goblin_golem": 3,
    # Dwarven Mines ── Bracket 5
    "golden_goblin": 4,
    # Dwarven Mines ── Bracket 7
    "diamond_goblin": 6, "littlefoot": 6,
    # ── Crystal Hollows ── Bracket 2
    "automaton": 1, "sludge": 1,
    # Crystal Hollows ── Bracket 3
    "thyst": 2, "yog": 2,
    # Crystal Hollows ── Bracket 4
    "butterfly": 3, "watcher": 3,
    # Crystal Hollows ── Bracket 5
    "worm": 4,
    # Crystal Hollows ── Bracket 6
    "bal": 5, "bal_boss": 5, "key_guardian": 5, "crystal_sentry": 5,
    # Crystal Hollows ── Bracket 7
    "boss_corleone": 6,
    # Crystal Hollows Team Treasurite ── Bracket 5
    "team_treasurite_grunt": 4, "team_treasurite_sebastian": 4,
    "team_treasurite_viper": 4, "team_treasurite_wendy": 4,
    # ── Fishing ── Bracket 2
    "squid": 1, "pond_squid": 1,
    # Fishing ── Bracket 3
    "small_mithril_grubber": 2, "medium_mithril_grubber": 2, "large_mithril_grubber": 2,
    "oasis_rabbit": 2, "oasis_sheep": 2, "sea_archer": 2, "sea_walker": 2,
    "sea_witch": 2, "rider_of_the_deep": 2,
    # Fishing ── Bracket 4
    "agarimoo": 3, "catfish": 3, "deep_sea_protector": 3, "frog_man": 3,
    "guardian_defender": 3, "inkling": 3, "manta_ray": 3, "sea_leech": 3,
    "sea_guardian": 3, "snapping_turtle": 3, "water_worm": 3,
    "poisoned_water_worm": 3, "trash_gobbler": 3,
    # Fishing ── Bracket 5
    "blue_ringed_octopus": 4, "carrot_king": 4, "water_hydra": 4,
    # Fishing ── Bracket 6
    "abyssal_miner": 5,
    # Fishing ── Bracket 7
    "wiki_tiki": 6,
    # Fishing Festival ── Bracket 3
    "nurse_shark": 2,
    # Fishing Festival ── Bracket 4
    "blue_shark": 3, "tiger_shark": 3,
    # Fishing Festival ── Bracket 5
    "great_white_shark": 4,
    # ── The Park ── Bracket 2
    "howling_spirit": 1, "pack_spirit": 1,
    # The Park ── Bracket 4
    "soul_of_the_alpha": 3,
    # ── Catacombs ── Bracket 1
    "skeleton_soldier": 0, "zombie_soldier": 0, "terracotta": 0,
    # Catacombs ── Bracket 2
    "undead": 1,
    # Catacombs ── Bracket 3
    "scared_skeleton": 2, "skeleton_grunt": 2, "sniper": 2,
    "tank_zombie": 2, "zombie_grunt": 2,
    # Catacombs ── Bracket 4
    "cellar_spider": 3, "crypt_dreadlord": 3, "crypt_lurker": 3,
    "crypt_souleater": 3, "fels": 3, "golem": 3, "lonely_spider": 3,
    "mimic": 3, "skeleton_master": 3, "super_tank_zombie": 3,
    "undead_skeleton": 3, "wither_miner": 3, "withermancer": 3, "zombie_commander": 3,
    # Catacombs ── Bracket 5
    "skeleton_lord": 4, "skeletor": 4, "super_archer": 4, "wither_guard": 4,
    "wither_husk": 4, "zombie_knight": 4, "zombie_lord": 4,
    # Catacombs ── Bracket 6
    "king_midas": 5,
    # Catacombs ── Bracket 7
    "angry_archeologist": 6, "lost_adventurer": 6, "shadow_assassin": 6,
    # ── Garden ── Bracket 6
    "beetle": 5, "cricket": 5, "dragonfly": 5, "earthworm": 5, "firefly": 5,
    "fly": 5, "locust": 5, "mite": 5, "mosquito": 5, "moth": 5,
    "praying_mantis": 5, "rat": 5, "slug": 5,
    "pest_beetle": 5, "pest_cricket": 5, "pest_fly": 5, "pest_locust": 5,
    "pest_mite": 5, "pest_mosquito": 5, "pest_moth": 5, "pest_rat": 5,
    # Garden ── Bracket 7
    "field_mouse": 6, "lunar_moth": 6, "timestalk_clone": 6, "zombuddy": 6,
    # ── Spooky Festival ── Bracket 2
    "crazy_witch": 1, "phantom_spirit": 1, "scary_jerry": 1,
    "trick_or_treater": 1, "wither_gourd": 1, "wraith": 1,
    # Spooky Festival ── Bracket 7
    "headless_horseman": 6,
    # ── Jerry Event ──
    "mayor_jerry_green": 3, "green_jerry": 3,    # Bracket 4
    "mayor_jerry_blue": 4, "blue_jerry": 4,       # Bracket 5
    "mayor_jerry_purple": 5, "purple_jerry": 5,   # Bracket 6
    "mayor_jerry_golden": 6, "golden_jerry": 6,   # Bracket 7
    # ── Backwater Bayou ── Bracket 4
    "banshee": 3, "bayou_sludge": 3, "dumpster_diver": 3,
    "chicken_deep": 3, "trash_gobbler": 3,
    # Backwater Bayou ── Bracket 7
    "titanoboa": 6,
    # ── Kuudra ── Bracket 2
    "kuudra_follower": 1,
    # Kuudra ── Bracket 3
    "blazing_golem": 2, "blight": 2, "dropship": 2, "explosive_imp": 2,
    "inferno_magma_cube": 2, "kuudra_berserker": 2, "kuudra_knocker": 2,
    "kuudra_landmine": 2, "kuudra_slasher": 2,
    # Kuudra ── Bracket 4
    "wandering_blaze": 3, "wither_sentry": 3,
    # Kuudra ── Bracket 5
    "magma_follower": 4,
    # ── Spooky Fishing ── Bracket 3
    "jumpin_jack": 2, "scarecrow": 2,
    # Spooky Fishing ── Bracket 4
    "nightmare": 3, "werewolf": 3,
    # Spooky Fishing ── Bracket 6
    "phantom_fisher": 5,
    # Spooky Fishing ── Bracket 7
    "grim_reaper": 6,
    # ── Lava Fishing ── Bracket 2
    "magma_slug": 1,
    # Lava Fishing ── Bracket 3
    "flaming_worm": 2, "lava_leech": 2, "moogma": 2,
    # Lava Fishing ── Bracket 4
    "fire_eel": 3, "fireproof_witch": 3, "fried_chicken": 3, "lava_blaze": 3,
    "lava_flame": 3, "lava_pigman": 3, "pyroclastic_worm": 3, "taurus": 3,
    # Lava Fishing ── Bracket 5
    "fiery_scuttler": 4, "thunder": 4,
    # Lava Fishing ── Bracket 7
    "lord_jawbus": 6, "phlegblast": 6, "ragnarok": 6,
    # ── Winter Event ── Bracket 4
    "frosty": 3, "frozen_steve": 3, "grinch": 3, "nutcracker": 3,
    # Winter Event ── Bracket 7
    "reindrake": 6, "yeti": 6,
    # ── Galatea ── Bracket 4
    "bogged": 3, "chill": 3, "ent": 3, "stridersurfer": 3,
    "tadgang": 3, "tidetot": 3, "wetwing": 3, "chillblade": 3, "chillshot": 3,
    # Galatea ── Bracket 5
    "the_loch_emperor": 4,
    # Galatea ── Bracket 7
    "nessie": 6,
    # ── Lotus Atoll ── Bracket 3
    "lotusfish": 2,
    # Lotus Atoll ── Bracket 4
    "atoll_croaker": 3, "drowned_captain": 3, "lotus_guardian": 3,
    "seashine": 3, "gorf": 3,
    # Lotus Atoll ── Bracket 5
    "puddle_jumper": 4,
    # Lotus Atoll ── Bracket 7
    "frog_prince": 6,
    # Lotus Atoll ── Bracket 8
    "lotum": 7,
    # ── Mythological ── Bracket 4
    "cretan_bull": 3, "gaia_construct": 3, "harpy": 3,
    "minos_hunter": 3, "minotaur": 3, "siamese_lynx": 3,
    # Mythological ── Bracket 5
    "minos_champion": 4,
    # Mythological ── Bracket 7
    "minos_inquisitor": 6, "sphinx": 6,
}

_DEFAULT_BRACKET = 1  # Bracket 2 for any unrecognised family


class Bestiary:
    def __init__(self, member_data: dict):
        kills = deep_get(member_data, ["bestiary", "kills"], default={})
        self._level = self._calculate(kills)

    def _calculate(self, kills: dict) -> float:
        families: dict[str, int] = {}
        for key, count in kills.items():
            if not isinstance(count, (int, float)):
                continue
            family = re.sub(r'_\d+$', '', key)
            if family:
                families[family] = families.get(family, 0) + int(count)

        total_completed = 0
        partial_kills = 0
        partial_needed = 0

        for family, total_kills in families.items():
            thresholds = _BRACKETS[_FAMILY_BRACKET.get(family, _DEFAULT_BRACKET)]
            completed = sum(1 for t in thresholds if total_kills >= t)
            total_completed += completed
            if completed < len(thresholds):
                prev = thresholds[completed - 1] if completed > 0 else 0
                partial_kills += total_kills - prev
                partial_needed += thresholds[completed] - prev

        fractional = partial_kills / partial_needed if partial_needed else 0.0
        return total_completed + fractional

    @property
    def level(self) -> float:
        return self._level
