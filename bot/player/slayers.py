from lib import deep_get


class Slayers:
    def __init__(self, uuid: str, selected_profile: dict):
        self.__uuid = uuid
        self.__selected_profile = selected_profile
        self._levels = self.__get_slayers()

    def __get_slayers(self) -> dict[str, int]:
        bosses = deep_get(self.__selected_profile, ["members", self.__uuid, "slayer", "slayer_bosses"], default={})
        return {
            "zombie": min(len(deep_get(bosses, ["zombie", "claimed_levels"], default=[])), 9),
            "spider": len(deep_get(bosses, ["spider", "claimed_levels"], default=[])),
            "wolf": len(deep_get(bosses, ["wolf", "claimed_levels"], default=[])),
            "enderman": len(deep_get(bosses, ["enderman", "claimed_levels"], default=[])),
            "blaze": len(deep_get(bosses, ["blaze", "claimed_levels"], default=[])),
            "vampire": len(deep_get(bosses, ["vampire", "claimed_levels"], default=[])),
        }

    @property
    def levels(self) -> str:
        s = self._levels
        return f"{s['zombie']}/{s['spider']}/{s['wolf']}/{s['enderman']}/{s['blaze']}/{s['vampire']}"
