import re
from lib import deep_get

_BRACKET = [250, 500, 1000, 2500, 5000, 10000]


class Bestiary:
    def __init__(self, member_data: dict):
        kills = deep_get(member_data, ["bestiary", "kills"], default={})
        self._level = self._calculate(kills)

    def _calculate(self, kills: dict) -> float:
        families: dict[str, int] = {}
        for key, count in kills.items():
            family = re.sub(r'_\d+$', '', key)
            if family:
                families[family] = families.get(family, 0) + int(count)

        score = 0.0
        for total_kills in families.values():
            completed = sum(1 for t in _BRACKET if total_kills >= t)
            score += completed
            if completed < len(_BRACKET):
                prev = _BRACKET[completed - 1] if completed > 0 else 0
                score += (total_kills - prev) / (_BRACKET[completed] - prev)

        return score

    @property
    def level(self) -> float:
        return self._level
