from lib import request, deep_get
from config import API_KEY


class Networth:
    def __init__(self, uuid: str, selected_profile: dict, bank: int, client):
        self.__uuid = uuid
        self.__selected_profile = selected_profile
        self.__bank = bank
        self.__cosmetic, self.__non_cosmetic = self.__get_networth(client)

    def __get_networth(self, client) -> tuple[int, int]:
        profile_id = self.__selected_profile.get("profile_id")
        profile_data = deep_get(self.__selected_profile, ["members", self.__uuid], default=None)

        if not profile_data or not profile_id:
            return 0, 0

        museum = request(f"https://api.hypixel.net/v2/skyblock/museum?profile={profile_id}&key={API_KEY}")
        museum_data = deep_get(museum, ["members", self.__uuid], default=None)

        if museum_data:
            calculator = client.skyhelper.ProfileNetworthCalculator(profile_data, museum_data, self.__bank)
        else:
            calculator = client.skyhelper.ProfileNetworthCalculator(profile_data, self.__bank)

        return round(calculator.getNetworth()["networth"]), round(calculator.getNonCosmeticNetworth()["networth"])

    @property
    def cosmetic_networth(self) -> int:
        return self.__cosmetic

    @property
    def non_cosmetic_networth(self) -> int:
        return self.__non_cosmetic
