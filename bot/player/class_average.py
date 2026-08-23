import base64
import io
import math

from nbt import nbt

from lib import deep_get
from constants import (
    ATTRIBUTE_LEVEL_THRESHOLDS,
    CATA_GRADUATE_MAX,
    CATA_GRADUATE_PER_LEVEL,
    CATA_GRADUATE_SHARD_RARITY,
    CLASS_PERK_KEYS,
    CLASS_PERK_MAX,
    CLASS_PERK_PER_LEVEL,
    DUNGEON_CLASSES,
    DUNGEON_XP_TABLE,
    HECATOMB_BASE,
    HECATOMB_MAX,
    HECATOMB_PER_LEVEL,
    SCARF_ACCESSORY_BOOSTS,
    SCARF_ACCESSORY_MAX,
)
# Imported for its import-time TAG_String._parse_buffer patch, which lets the NBT
# reader survive the non-UTF-8 item names Hypixel returns.
from player import magical_power as _nbt_patch  # noqa: F401

# XP gained by the four classes nobody is playing, as a fraction of the played class's XP.
PASSIVE_SHARE = 0.25

# Above this many projected runs the run-by-run simulation is replaced by the analytic
# solve, which lands on the same total without stalling the event loop. The cutoff keeps
# every mastermode floor and F7 on the exact simulation; only the low floors, where the
# answer is already in the hundreds of thousands of runs, take the analytic path.
_SIMULATION_LIMIT = 100_000

# Shard counts per attribute, confirmed against a live profile. Note this is a count of
# shards syphoned, not a level - see ATTRIBUTE_LEVEL_THRESHOLDS. The unrelated top-level
# "shards" object holds the shard inventory and does not carry attribute progress.
_ATTRIBUTE_STACKS_PATH = ["attributes", "stacks"]
_GRADUATE_KEY = "catacombs_graduate"

# Hecatomb sits on the gear a player wears *for dungeons*, which is rarely what they happen
# to have equipped when the profile is read - observed in the wild sitting in the ender chest
# and inside a backpack. Scan everywhere it can hide and take the best level found; missing
# one container silently undercounts the boost by 4%.
_HECATOMB_CONTAINERS = (
    ["inventory", "inv_armor", "data"],
    ["inventory", "equipment_contents", "data"],
    ["inventory", "wardrobe_contents", "data"],
    ["inventory", "inv_contents", "data"],
    ["inventory", "ender_chest_contents", "data"],
    ["inventory", "personal_vault_contents", "data"],
)
# Backpacks are a dict of {slot: {"data": ...}} rather than a fixed path.
_BACKPACKS_PATH = ["inventory", "backpack_contents"]


class ClassAverage:
    """Dungeon class XP, and how many runs remain until every class hits a target level.

    Mirrors the maths of the reference calculator (adjectiven0un/adjectils dungeon.html):
    each run, the class with the most XP remaining is the one being played and earns full
    XP, while the other four earn a quarter each.

    XP boosts are read off the profile where Hypixel exposes them. Where a whole container
    is missing - most often because the player has their inventory API switched off - the
    boost is assumed to be maxed, so the run count comes out optimistic rather than
    silently inflated.
    """

    def __init__(self, member_data: dict):
        self.__member_data = member_data
        self.__xp = {
            c: deep_get(member_data, ["dungeons", "player_classes", c, "experience"], default=0) or 0
            for c in DUNGEON_CLASSES
        }
        self.__boosts = self.__get_boosts()

    # ------------------------------------------------------------------ boosts

    def __get_boosts(self) -> dict[str, float]:
        """Additive XP boost per class, e.g. 0.4 meaning +40% class XP per run."""
        shared = self.__hecatomb() * 2 + self.__scarf_accessory() + self.__cata_graduate()
        perks = self.__class_perks()
        return {c: shared + perks[c] for c in DUNGEON_CLASSES}

    def __decode_items(self, path: list) -> list | None:
        raw = deep_get(self.__member_data, path, default=None)
        if not raw:
            return None
        try:
            return list(nbt.NBTFile(fileobj=io.BytesIO(base64.b64decode(raw)))["i"])
        except Exception:
            return None

    def __hecatomb(self) -> float:
        backpacks = deep_get(self.__member_data, _BACKPACKS_PATH, default={})
        paths = list(_HECATOMB_CONTAINERS)
        if isinstance(backpacks, dict):
            paths += [_BACKPACKS_PATH + [slot, "data"] for slot in backpacks]

        level, readable = 0, False
        for path in paths:
            items = self.__decode_items(path)
            if items is None:
                continue
            readable = True
            for item in items:
                try:
                    level = max(level, int(item["tag"]["ExtraAttributes"]["enchantments"]["hecatomb"].value))
                except Exception:
                    continue

        if not readable:
            return HECATOMB_MAX
        if level <= 0:
            return 0.0
        return min(HECATOMB_MAX, HECATOMB_BASE + (level - 1) * HECATOMB_PER_LEVEL)

    def __scarf_accessory(self) -> float:
        items = self.__decode_items(["inventory", "bag_contents", "talisman_bag", "data"])
        if items is None:
            return SCARF_ACCESSORY_MAX

        boost = 0.0
        for item in items:
            try:
                item_id = str(item["tag"]["ExtraAttributes"]["id"].value)
            except Exception:
                continue
            boost = max(boost, SCARF_ACCESSORY_BOOSTS.get(item_id, 0.0))
        return boost

    def __class_perks(self) -> dict[str, float]:
        perks = deep_get(self.__member_data, ["player_data", "perks"], default=None)
        if not isinstance(perks, dict):
            return {c: CLASS_PERK_MAX for c in DUNGEON_CLASSES}
        return {
            c: min(CLASS_PERK_MAX, int(perks.get(CLASS_PERK_KEYS[c], 0) or 0) * CLASS_PERK_PER_LEVEL)
            for c in DUNGEON_CLASSES
        }

    def __cata_graduate(self) -> float:
        stacks = deep_get(self.__member_data, _ATTRIBUTE_STACKS_PATH, default=None)
        if not isinstance(stacks, dict):
            return CATA_GRADUATE_MAX

        owned = int(stacks.get(_GRADUATE_KEY, 0) or 0)
        thresholds = ATTRIBUTE_LEVEL_THRESHOLDS[CATA_GRADUATE_SHARD_RARITY]
        level = sum(1 for required in thresholds if owned >= required)
        return min(CATA_GRADUATE_MAX, level * CATA_GRADUATE_PER_LEVEL)

    # ------------------------------------------------------------------ levels

    @staticmethod
    def target_xp(level: int) -> int:
        """Total class XP required to reach a class level. Classes cap at 50."""
        return DUNGEON_XP_TABLE[min(level, 50)]

    @property
    def levels(self) -> dict[str, int]:
        return {
            c: [k for k, v in DUNGEON_XP_TABLE.items() if xp >= v][-1]
            for c, xp in self.__xp.items()
        }

    @property
    def class_average(self) -> float:
        levels = self.levels
        return round(sum(levels.values()) / len(levels), 2)

    # ------------------------------------------------------------------ runs

    def xp_per_run(self, floor_xp: int, mayor_multiplier: float = 1.0) -> dict[str, float]:
        multiplier = min(1.5, mayor_multiplier)
        return {c: floor_xp * ((1 + boost) * multiplier) for c, boost in self.__boosts.items()}

    def runs_to_target(self, floor_xp: int, target_level: int = 50, mayor_multiplier: float = 1.0,
                       playable: tuple[str, ...] = DUNGEON_CLASSES) -> tuple[int, dict[str, int]]:
        """Runs needed for every class to reach target_level, restricted to playing `playable`.

        `playable` defaults to all 5 (.rtca). `.rtcaf` passes a subset to permanently exclude
        classes from ever being the "played" pick - excluded classes still take their normal
        passive quarter share every run, so they keep climbing toward target_level, just slower,
        which means excluding classes can only raise the total run count, never lower it.
        """
        target = self.target_xp(target_level)
        remaining = {c: max(target - self.__xp[c], 0.0) for c in DUNGEON_CLASSES}
        if not any(remaining.values()):
            return 0, {c: 0 for c in playable}

        per_run = self.xp_per_run(floor_xp, mayor_multiplier)
        if min(per_run.values()) <= 0:
            raise ValueError("projected class XP per run is zero")

        estimate = self.__solve_total_runs(remaining, per_run, playable)
        if estimate > _SIMULATION_LIMIT:
            return estimate, self.__split_runs(remaining, per_run, estimate, playable)
        return self.__simulate(remaining, per_run, playable)

    def minimum_runs_needed(self, floor_xp: int, total: int, target_level: int = 50,
                            mayor_multiplier: float = 1.0,
                            playable: tuple[str, ...] = DUNGEON_CLASSES) -> dict[str, int]:
        """Fewest dedicated plays each playable class needs to reach target_level, given a
        `total` run count already established by runs_to_target().

        Once a class's minimum is met it doesn't matter which playable class the remaining runs
        go to - the passive share every non-played class earns depends only on the total run
        count, not on which other class was actually played. A class needing 0 means the total
        is already large enough that passive share alone (from whatever else gets played) covers
        it - there's nothing to dedicate to it specifically.
        """
        target = self.target_xp(target_level)
        remaining = {c: max(target - self.__xp[c], 0.0) for c in DUNGEON_CLASSES}
        per_run = self.xp_per_run(floor_xp, mayor_multiplier)
        return self.__runs_needed(remaining, per_run, total, playable)

    @staticmethod
    def __simulate(remaining: dict[str, float], per_run: dict[str, float],
                   playable: tuple[str, ...]) -> tuple[int, dict[str, int]]:
        """Replay the reference calculator's run-by-run greedy loop, restricted to `playable`."""
        left = dict(remaining)
        runs = {c: 0 for c in playable}
        while any(v > 0 for v in left.values()):
            # max() keeps the first of any tie, matching the reference's strict comparison.
            played = max(playable, key=lambda c: left[c])
            for c in DUNGEON_CLASSES:
                left[c] -= per_run[c] if c == played else per_run[c] * PASSIVE_SHARE
            runs[played] += 1
        return sum(runs.values()), runs

    @staticmethod
    def __runs_needed(remaining: dict[str, float], per_run: dict[str, float], total: int,
                      playable: tuple[str, ...]) -> dict[str, int]:
        """Runs that must be played on each playable class given `total` runs overall.

        Over `total` runs a class gains `played * per_run + (total - played) * per_run/4`,
        so the played runs it needs are (remaining/per_run - total/4) / (1 - 1/4).
        """
        needed = {}
        for c in playable:
            deficit = remaining[c] / per_run[c] - total * PASSIVE_SHARE
            needed[c] = max(0, math.ceil(deficit / (1 - PASSIVE_SHARE)))
        return needed

    @staticmethod
    def __skip_threshold(remaining: dict[str, float], per_run: dict[str, float],
                         skipped: tuple[str, ...]) -> int:
        """Smallest total run count by which every permanently-skipped class's passive-only
        XP (it is never played, so it only ever earns the quarter share) clears target."""
        if not skipped:
            return 0
        return max(math.ceil(remaining[c] / (per_run[c] * PASSIVE_SHARE)) for c in skipped)

    @classmethod
    def __solve_total_runs(cls, remaining: dict[str, float], per_run: dict[str, float],
                           playable: tuple[str, ...]) -> int:
        """Smallest total run count whose per-playable-class requirements fit inside it,
        raised to cover whatever any permanently-skipped class needs on passive share alone."""
        high = 1
        while sum(cls.__runs_needed(remaining, per_run, high, playable).values()) > high:
            high *= 2
        low = high // 2
        while low < high:
            mid = (low + high) // 2
            if sum(cls.__runs_needed(remaining, per_run, mid, playable).values()) <= mid:
                high = mid
            else:
                low = mid + 1

        skipped = tuple(c for c in DUNGEON_CLASSES if c not in playable)
        return max(low, cls.__skip_threshold(remaining, per_run, skipped))

    @classmethod
    def __split_runs(cls, remaining: dict[str, float], per_run: dict[str, float],
                     total: int, playable: tuple[str, ...]) -> dict[str, int]:
        runs = cls.__runs_needed(remaining, per_run, total, playable)
        # Any run the requirements don't account for still has to be played on some class;
        # the greedy loop would spend it on whichever playable class finishes last.
        slack = total - sum(runs.values())
        if slack > 0:
            slowest = max(playable, key=lambda c: remaining[c] / per_run[c])
            runs[slowest] += slack
        return runs
