from lib import deep_get


class SkyblockLevel:
    def __init__(self, member_data: dict, all_member_data: list[tuple[dict, str]]):
        xp = deep_get(member_data, ["leveling", "experience"], default=0)
        self.__current = xp / 100
        self.__highest, self.__gamemode = self.__get_highest(all_member_data)

    def __get_highest(self, all_member_data: list[tuple[dict, str]]) -> tuple[float, str]:
        highest, gamemode = 0.0, ""
        for data, gm in all_member_data:
            xp = deep_get(data, ["leveling", "experience"], default=0)
            level = xp / 100
            if level > highest:
                highest, gamemode = level, gm
        return highest, gamemode

    @property
    def current(self) -> float:
        return self.__current

    @property
    def highest(self) -> tuple[float, str]:
        return self.__highest, self.__gamemode
