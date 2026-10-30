"""Shared (not per-guild) panel-editable settings, merged over built-in defaults.

Stored in `bot_settings` (one JSON value per key). Both processes read through a short cache,
so a change made on the panel's Config page reaches the bot within CACHE_SECONDS without a
restart. Per-guild settings live in lib/guild_settings.py instead."""
import re
import time

from db import manager

CACHE_SECONDS = 20

WARPOUT_DEFAULTS = {
    "guild": "bu",          # whose bridge bot performs every .warpout
    "max_queue": 10,        # waiting + running requests
    "invite_timeout": 60,   # seconds to wait for the player to join the party (Hypixel expires invites at 60s)
}
CENSOR_DEFAULTS = {"words": []}  # extra words on top of lib/censor.py's built-in list

_WORD_RE = re.compile(r"^[a-z0-9]{2,30}$")
_cache: dict = {}


def _stored(key: str) -> dict:
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]
    row = manager.get_setting(key)
    value = row["value"] if row else {}
    _cache[key] = (time.time(), value)
    return value


def invalidate(key: str) -> None:
    _cache.pop(key, None)


def get_warpout() -> dict:
    stored = _stored("warpout")
    return {k: stored.get(k, d) for k, d in WARPOUT_DEFAULTS.items()}


def get_censor_words() -> list[str]:
    return list(_stored("censor").get("words", CENSOR_DEFAULTS["words"]))


def validate_warpout(values: dict, guild_keys) -> dict:
    """Returns the cleaned settings; raises ValueError with a user-facing message."""
    unknown = set(values) - set(WARPOUT_DEFAULTS)
    if unknown:
        raise ValueError(f"Unknown warpout setting: {', '.join(sorted(unknown))}")
    merged = {k: values.get(k, d) for k, d in WARPOUT_DEFAULTS.items()}
    if merged["guild"] not in guild_keys:
        raise ValueError("Warpout bot must be one of the guilds")
    for k in ("max_queue", "invite_timeout"):
        v = merged[k]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or int(v) != v:
            raise ValueError(f"{k}: must be a whole number")
        merged[k] = int(v)
    if not 1 <= merged["max_queue"] <= 50:
        raise ValueError("Queue size must be between 1 and 50")
    if not 10 <= merged["invite_timeout"] <= 60:
        raise ValueError("Invite timeout must be between 10 and 60 seconds (Hypixel expires invites at 60)")
    return merged


def validate_censor(words) -> dict:
    if not isinstance(words, list):
        raise ValueError("Censored words must be a list")
    cleaned = []
    for w in words:
        w = str(w).strip().lower()
        if not w:
            continue
        if not _WORD_RE.match(w):
            raise ValueError(f"'{w}': censored words are 2-30 letters or digits, one word each")
        if w not in cleaned:
            cleaned.append(w)
    if len(cleaned) > 200:
        raise ValueError("At most 200 extra censored words")
    return {"words": cleaned}
