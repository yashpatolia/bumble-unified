from lib import deep_get
from constants import GAMEMODE


class SkyblockLevel:
    def __init__(self, uuid: str, profiles: list, selected_profile: dict):
        self.__uuid = uuid
        self.__profiles = profiles
        self.__selected_profile = selected_profile

        self.__current = self.__get_current()
        self.__highest, self.__gamemode = self.__get_highest()

    def __get_current(self) -> float:
        xp = deep_get(self.__selected_profile, ["members", self.__uuid, "leveling", "experience"], default=0)
        return xp / 100

    def __get_highest(self) -> tuple[float, str]:
        highest, gamemode = 0.0, ""
        for profile in self.__profiles:
            xp = deep_get(profile, ["members", self.__uuid, "leveling", "experience"], default=0)
            level = xp / 100
            if level > highest:
                highest = level
                gamemode = GAMEMODE[profile.get("game_mode", "")]
        return highest, gamemode

    @property
    def current(self) -> float:
        return self.__current

    @property
    def highest(self) -> tuple[float, str]:
        return self.__highest, self.__gamemode
