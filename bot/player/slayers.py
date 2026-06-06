from lib import deep_get

_ALIASES: dict[str, str] = {
    "rev": "zombie", "revenant": "zombie", "zombie": "zombie",
    "spider": "spider", "tara": "spider", "tarantula": "spider",
    "wolf": "wolf", "sven": "wolf",
    "eman": "enderman", "enderman": "enderman", "voidgloom": "enderman",
    "blaze": "blaze", "inferno": "blaze",
    "vamp": "vampire", "vampire": "vampire", "riftstalker": "vampire", "rift": "vampire",
}

_DISPLAY: dict[str, str] = {
    "zombie": "Revenant", "spider": "Tarantula", "wolf": "Sven",
    "enderman": "Voidgloom", "blaze": "Inferno", "vampire": "Riftstalker",
}


class Slayers:
    def __init__(self, member_data: dict):
        bosses = deep_get(member_data, ["slayer", "slayer_bosses"], default={})
        self._levels = {
            "zombie":   min(len(deep_get(bosses, ["zombie",   "claimed_levels"], default=[])), 9),
            "spider":   len(deep_get(bosses, ["spider",   "claimed_levels"], default=[])),
            "wolf":     len(deep_get(bosses, ["wolf",     "claimed_levels"], default=[])),
            "enderman": len(deep_get(bosses, ["enderman", "claimed_levels"], default=[])),
            "blaze":    len(deep_get(bosses, ["blaze",    "claimed_levels"], default=[])),
            "vampire":  len(deep_get(bosses, ["vampire",  "claimed_levels"], default=[])),
        }
        self._xp = {
            key: deep_get(bosses, [key, "xp"], default=0)
            for key in self._levels
        }

    @property
    def levels(self) -> str:
        s = self._levels
        return f"{s['zombie']}/{s['spider']}/{s['wolf']}/{s['enderman']}/{s['blaze']}/{s['vampire']}"

    def xp_for(self, alias: str) -> tuple[str, int] | None:
        """Return (display_name, xp) for a slayer alias, or None if unrecognised."""
        key = _ALIASES.get(alias.lower())
        if key is None:
            return None
        return _DISPLAY[key], self._xp[key]
