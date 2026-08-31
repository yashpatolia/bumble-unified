import math

from lib import deep_get
from constants import DUNGEON_XP_TABLE, DUNGEON_INDIVIDUAL_XP_TABLE


class Catacombs:
    def __init__(self, member_data: dict, all_member_data: list[tuple[dict, str]]):
        self.__member_data = member_data
        self.__all_member_data = all_member_data

        self.__cata_xp = deep_get(
            member_data, ["dungeons", "dungeon_types", "catacombs", "experience"], default=0
        )
        self.__cata_level = self.__get_cata_level()
        self.__secrets = deep_get(member_data, ["dungeons", "secrets"], default=0)
        self.__total_runs = self.__get_total_runs()

    def __get_cata_level(self) -> float:
        cata_xp = self.__cata_xp
        level = [k for k, v in DUNGEON_XP_TABLE.items() if cata_xp >= v][-1]

        if level >= 50:
            xp_past_50 = cata_xp - DUNGEON_XP_TABLE[50]
            level = 50 + round(xp_past_50 / 200_000_000, 2)
        else:
            level += round((cata_xp - DUNGEON_XP_TABLE[level]) / DUNGEON_INDIVIDUAL_XP_TABLE[level + 1], 2)

        return level

    def runs_to_level(self, floor_xp: int, target_level: int = 50, mayor_multiplier: float = 1.0,
                      boost: float = 0.0) -> int:
        """Runs needed to reach target_level Catacombs from the currently-earned raw Catacombs XP."""
        target = DUNGEON_XP_TABLE[min(target_level, 50)]
        remaining = max(target - self.__cata_xp, 0.0)
        if remaining == 0:
            return 0

        per_run = floor_xp * (1 + boost) * min(1.5, mayor_multiplier)
        if per_run <= 0:
            raise ValueError("projected Catacombs XP per run is zero")
        return math.ceil(remaining / per_run)

    def __get_total_runs(self) -> int:
        def count_runs(path):
            runs = deep_get(self.__member_data, path, default={})
            return int(sum(runs.values())) - int(runs.get("total", 0))

        base = ["dungeons", "dungeon_types"]
        return (
            count_runs(base + ["catacombs", "tier_completions"])
            + count_runs(base + ["master_catacombs", "tier_completions"])
        )

    def pb(self, floor_type: str, floor) -> tuple[str, str, str, str]:
        convert_ms = lambda ms: (ms // 60000, (ms % 60000) // 1000)
        catacombs_type = "master_catacombs" if floor_type.lower() == "m" else "catacombs"
        s_plus, s, comp = float("inf"), float("inf"), float("inf")

        for data, _ in self.__all_member_data:
            dungeon_data = deep_get(data, ["dungeons", "dungeon_types", catacombs_type], default={})
            sp = deep_get(dungeon_data, ["fastest_time_s_plus", floor], default=float("inf"))
            st = deep_get(dungeon_data, ["fastest_time_s", floor], default=float("inf"))
            ct = deep_get(dungeon_data, ["fastest_time", floor], default=float("inf"))
            if sp < s_plus: s_plus = sp
            if st < s: s = st
            if ct < comp: comp = ct

        fmt = lambda t: f"{convert_ms(int(t))[0]}:{convert_ms(int(t))[1]:02d}" if t not in (0, float("inf")) else "None"
        s_plus = 0 if s_plus == float("inf") else s_plus
        s = 0 if s == float("inf") else s
        comp = 0 if comp == float("inf") else comp

        return fmt(s_plus), fmt(s), fmt(comp), catacombs_type.replace("_", " ").title()

    @property
    def level(self) -> float:
        return self.__cata_level

    @property
    def secrets(self) -> int:
        return self.__secrets

    @property
    def spr(self) -> float:
        return round(self.__secrets / self.__total_runs, 2) if self.__total_runs else 0.0
