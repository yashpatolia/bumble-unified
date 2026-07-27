from lib import request, deep_get
from config import API_KEY


class Networth:
    def __init__(self, uuid: str, member_data: dict, profile_id: str | None, bank: int, skyhelper):
        self.__cosmetic, self.__non_cosmetic = self.__get_networth(uuid, member_data, profile_id, bank, skyhelper)

    def __get_networth(self, uuid: str, member_data: dict, profile_id: str | None, bank: int, skyhelper) -> tuple[int, int]:
        if not member_data or not profile_id:
            return 0, 0

        from db import manager
        museum = request(f"https://api.hypixel.net/v2/skyblock/museum?profile={profile_id}&key={API_KEY}")
        manager.record_api_call("/v2/skyblock/museum", bool(museum.get("success")))
        museum_data = deep_get(museum, ["members", uuid], default=None)

        if museum_data:
            calculator = skyhelper.ProfileNetworthCalculator(member_data, museum_data, bank)
        else:
            calculator = skyhelper.ProfileNetworthCalculator(member_data, bank)

        return round(calculator.getNetworth()["networth"]), round(calculator.getNonCosmeticNetworth()["networth"])

    @property
    def cosmetic_networth(self) -> int:
        return self.__cosmetic

    @property
    def non_cosmetic_networth(self) -> int:
        return self.__non_cosmetic
