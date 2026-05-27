from lib import deep_get
from constants import DUNGEON_XP_TABLE, DUNGEON_INDIVIDUAL_XP_TABLE


class Catacombs:
    def __init__(self, uuid: str, profiles: list, selected_profile: dict):
        self.__uuid = uuid
        self.__profiles = profiles
        self.__selected_profile = selected_profile

        self.__cata_level = self.__get_cata_level()
        self.__secrets = self.__get_secrets()
        self.__total_runs = self.__get_total_runs()

    def __get_cata_level(self) -> float:
        cata_xp = deep_get(
            self.__selected_profile,
            ["members", self.__uuid, "dungeons", "dungeon_types", "catacombs", "experience"],
            default=0,
        )
        level = [k for k, v in DUNGEON_XP_TABLE.items() if cata_xp >= v][-1]

        if level >= 50:
            xp_past_50 = cata_xp - DUNGEON_XP_TABLE[50]
            if cata_xp > DUNGEON_XP_TABLE[50]:
                level = 50 + round(xp_past_50 / 200_000_000, 2)
            elif level == 50 and cata_xp < DUNGEON_XP_TABLE[51]:
                level += round((cata_xp - DUNGEON_XP_TABLE[50]) / DUNGEON_INDIVIDUAL_XP_TABLE[51], 2)
        else:
            level += round((cata_xp - DUNGEON_XP_TABLE[level]) / DUNGEON_INDIVIDUAL_XP_TABLE[level + 1], 2)

        return level

    def __get_secrets(self) -> int:
        return deep_get(self.__selected_profile, ["members", self.__uuid, "dungeons", "secrets"], default=0)

    def __get_total_runs(self) -> int:
        def count_runs(path):
            runs = deep_get(self.__selected_profile, path, default={})
            return int(sum(runs.values())) - int(runs.get("total", 0))

        base = ["members", self.__uuid, "dungeons", "dungeon_types"]
        return count_runs(base + ["catacombs", "tier_completions"]) + count_runs(base + ["master_catacombs", "tier_completions"])

    def pb(self, floor_type: str, floor: int) -> tuple[str, str, str, str]:
        convert_ms = lambda ms: (ms // 60000, (ms % 60000) // 1000)
        catacombs_type = "master_catacombs" if floor_type.lower() == "m" else "catacombs"
        s_plus, s, comp = float("inf"), float("inf"), float("inf")

        for profile in self.__profiles:
            data = deep_get(profile, ["members", self.__uuid, "dungeons", "dungeon_types", catacombs_type], default=[])
            sp = deep_get(data, ["fastest_time_s_plus", floor], default=float("inf"))
            st = deep_get(data, ["fastest_time_s", floor], default=float("inf"))
            ct = deep_get(data, ["fastest_time", floor], default=float("inf"))
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
