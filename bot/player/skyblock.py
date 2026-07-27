from config import API_KEY
from constants import GAMEMODE
from lib import get_uuid, get_username, deep_get, request
from player.level import SkyblockLevel
from player.networth import Networth
from player.catacombs import Catacombs
from player.slayers import Slayers
from player.magical_power import MagicalPower


class PlayerNotFoundError(Exception):
    """Raised when a username/uuid can't be resolved to a Mojang account."""


class HypixelAPIError(Exception):
    """Raised when the Hypixel API rejects or fails a request (e.g. bad key, API down)."""


def _prune_large_blobs(value):
    """Strip base64-encoded gzip NBT item data (inventory/backpack/wardrobe/vault contents,
    always stored under a "data" key) from a profile member object -- keeps every other
    field so callers can dig for a stat with no dedicated Player property yet.
    """
    if isinstance(value, dict):
        return {
            k: _prune_large_blobs(v)
            for k, v in value.items()
            if not (k == "data" and isinstance(v, str) and len(v) > 200)
        }
    if isinstance(value, list):
        return [_prune_large_blobs(v) for v in value[:50]]
    return value


class Player:
    def __init__(self, uuid: str = None, username: str = None):
        self.__uuid = uuid or get_uuid(username=username)
        if not self.__uuid:
            raise PlayerNotFoundError(username or uuid)
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
        from db import manager
        data = request(f"https://api.hypixel.net/v2/skyblock/profiles?uuid={self.uuid}&key={API_KEY}")
        success = bool(data.get("success"))
        manager.record_api_call("/v2/skyblock/profiles", success)
        if not success:
            raise HypixelAPIError(data.get("cause") or "Hypixel API request failed")
        return data.get("profiles") or []

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
        return deep_get(self.__member_data, ["leveling", "highest_pet_score"], default=0)

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

    @property
    def raw_skill_experience(self) -> dict:
        """Best-effort dump of every skill-XP-looking field on the profile.

        This codebase doesn't maintain a skill level table (mining/foraging/farming/etc.),
        so unlike level/catacombs/slayers this returns raw XP rather than a computed level.
        Callers that need an actual level should pair this with the skill's wiki page, which
        documents the XP-per-level breakpoints.
        """
        skills = {
            k: v for k, v in self.__member_data.items()
            if "skill" in k.lower() and isinstance(v, (int, float))
        }
        experience = deep_get(self.__member_data, ["player_data", "experience"], default={})
        if isinstance(experience, dict):
            skills.update({k: v for k, v in experience.items() if isinstance(v, (int, float))})
        return skills

    @property
    def raw_member_data(self) -> dict:
        """Full profile member object for the selected profile, minus large binary item blobs.

        Fallback for stats that don't have a dedicated Player property (Magic Find, pet luck,
        individual accessory bonuses, etc.) -- used by lib/wiki_qa.py's get_player_raw_data
        tool so Claude can search the real Hypixel response instead of being limited to
        whatever this class happens to expose already.
        """
        return _prune_large_blobs(self.__member_data)

