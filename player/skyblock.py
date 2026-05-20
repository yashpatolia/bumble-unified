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
        return SkyblockLevel(self.__uuid, self.__profiles, self.__selected_profile)

    @property
    def purse(self) -> int:
        return round(deep_get(self.__selected_profile, ["members", self.__uuid, "currencies", "coin_purse"], 0))

    @property
    def bank(self) -> int:
        return round(deep_get(self.__selected_profile, ["banking", "balance"], 0))

    @property
    def personal_bank(self) -> int:
        return round(deep_get(self.__selected_profile, ["members", self.__uuid, "profile", "bank_account"], 0))

    def networth(self, client) -> Networth:
        return Networth(self.__uuid, self.__selected_profile, self.bank, client)

    @property
    def catacombs(self) -> Catacombs:
        return Catacombs(self.__uuid, self.__profiles, self.__selected_profile)

    @property
    def slayers(self) -> Slayers:
        return Slayers(self.__uuid, self.__selected_profile)

    @property
    def magical_power(self) -> MagicalPower:
        return MagicalPower(self.__uuid, self.__selected_profile)
