from config import API_KEY
from constants import GAMEMODE
from lib import get_uuid, get_username, deep_get, request
from player.level import SkyblockLevel
from player.networth import Networth
from player.catacombs import Catacombs
from player.slayers import Slayers
from player.magical_power import MagicalPower


class Player:
    def __init__(self, uuid: str = None, username: str = None):
        self.__uuid = uuid or get_uuid(username=username)
        self.__username = username or get_username(uuid=uuid)

        self.__profiles = self.__fetch_skyblock_profiles()
        self.__selected_profile, self.__gamemode = self.__get_selected_profile()

        # Pre-slice member data so subclasses receive only what they need
        self.__member_data = (
            self.__selected_profile.get("members", {}).get(self.__uuid, {})
            if self.__selected_profile else {}
        )
        self.__all_member_data: list[tuple[dict, str]] = [
            (p.get("members", {}).get(self.__uuid, {}), GAMEMODE[p.get("game_mode", "")])
            for p in self.__profiles
        ]

        # Cache subclasses — constructing on every property access re-runs all computation
        self._level = SkyblockLevel(self.__member_data, self.__all_member_data)
        self._catacombs = Catacombs(self.__member_data, self.__all_member_data)
        self._slayers = Slayers(self.__member_data)
        self._magical_power = MagicalPower(self.__member_data)

    def __fetch_skyblock_profiles(self) -> list:
        data = request(f"https://api.hypixel.net/v2/skyblock/profiles?uuid={self.uuid}&key={API_KEY}")
        return data["profiles"] or []

    def __get_selected_profile(self) -> tuple[dict | None, str]:
        for profile in self.__profiles:
            if profile["selected"]:
                return profile, GAMEMODE[profile.get("game_mode", "")]
        return None, ""

    @property
    def uuid(self) -> str:
        return self.__uuid

    @property
    def username(self) -> str:
        return self.__username

    @property
    def get_profile_names(self) -> list[str]:
        return [profile["cute_name"] for profile in self.__profiles]

    def get_profile_id(self, profile_name: str) -> str | None:
        for profile in self.__profiles:
            if profile["cute_name"].lower() == profile_name.lower():
                return profile["profile_id"]
        return None

    @property
    def gamemode(self) -> str:
        return self.__gamemode

    @property
    def level(self) -> SkyblockLevel:
        return self._level

    @property
    def pet_score(self) -> int:
        return deep_get(self.__member_data, ["player_data", "leveling", "highest_pet_score"], default=0)

    @property
    def purse(self) -> int:
        return round(deep_get(self.__member_data, ["currencies", "coin_purse"], 0))

    @property
    def bank(self) -> int:
        if not self.__selected_profile:
            return 0
        return round(deep_get(self.__selected_profile, ["banking", "balance"], 0))

    @property
    def personal_bank(self) -> int:
        return round(deep_get(self.__member_data, ["profile", "bank_account"], 0))

    def networth(self, skyhelper) -> Networth:
        profile_id = self.__selected_profile.get("profile_id") if self.__selected_profile else None
        return Networth(self.__uuid, self.__member_data, profile_id, self.bank, skyhelper)

    @property
    def catacombs(self) -> Catacombs:
        return self._catacombs

    @property
    def slayers(self) -> Slayers:
        return self._slayers

    @property
    def magical_power(self) -> MagicalPower:
        return self._magical_power
