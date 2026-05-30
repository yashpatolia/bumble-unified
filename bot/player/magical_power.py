import base64
import io
import math
import logging
from nbt import nbt
from nbt.nbt import TAG_String
from lib import deep_get
from constants import MP_VALUES


def _safe_parse_buffer(self, buffer):
    length = int.from_bytes(buffer.read(2), "big")
    raw = buffer.read(length)
    try:
        self.value = raw.decode("utf-8")
    except UnicodeDecodeError:
        self.value = raw.decode("latin-1")

TAG_String._parse_buffer = _safe_parse_buffer


class MagicalPower:
    def __init__(self, member_data: dict):
        self.__total, self.__highest = self.__get_magical_power(member_data)

    def __get_magical_power(self, member_data: dict) -> tuple[int, int]:
        raw = deep_get(
            member_data,
            ["inventory", "bag_contents", "talisman_bag", "data"],
            default=None,
        )
        if raw is None:
            return 0, 0

        highest_mp = deep_get(member_data, ["accessory_bag_storage", "highest_magical_power"], default=0)
        contacts = len(deep_get(member_data, ["nether_island_player_data", "abiphone", "active_contacts"], default=[]))
        prism = deep_get(member_data, ["rift", "access", "consumed_prism"], default=False)

        total_mp = 0
        abiphone = very_special = special = False
        seen_names: list[str] = []

        data = nbt.NBTFile(fileobj=io.BytesIO(base64.b64decode(raw)))
        for talisman in data["i"]:
            try:
                name = talisman["tag"]["display"]["Name"]
                if name[2:] in seen_names:
                    continue
                seen_names.append(name[2:])
                if "Abicase" in name:
                    abiphone = True

                rarity = talisman["tag"]["display"]["Lore"][-1]
                for key, value in MP_VALUES.items():
                    if key in rarity:
                        total_mp += (2 * value) if "Hegemony" in name else value
                        break
                    if "VERY SPECIAL" in rarity:
                        very_special = True
                    if "SPECIAL" in rarity:
                        special = True
            except Exception as e:
                logging.error(e)

        total_mp += math.floor(contacts / 2) if abiphone else 0
        total_mp += 11 if prism else 0
        total_mp += 5 if very_special else 0
        total_mp += 3 if special and not very_special else 0

        return min(total_mp, highest_mp), highest_mp

    @property
    def total(self) -> int:
        return self.__total

    @property
    def highest(self) -> int:
        return self.__highest
