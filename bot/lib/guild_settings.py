"""Panel-editable guild settings, merged over the built-in defaults.

Rank level requirements (every rank, lowest included) default to the env-driven values in
config.py (GuildConfig.ranks); the bot's Minecraft version defaults to MINECRAFT_VERSION;
the "needs attention" thresholds default to ATTENTION_DEFAULTS. Overrides live in the
`guild_config` table. Both the bot process (rank automation) and the panel process
(config page) use this module; the bot reads through a short cache so a change made in
the panel takes effect within CACHE_SECONDS without a restart."""
import time

from db import manager

CACHE_SECONDS = 20

ATTENTION_DEFAULTS = {
    "kick_risk_days": 60,      # offline this long (and in the bottom N by level) = kick risk
    "inactive_days": 30,
    "low_activity_days": 14,
    "bottom_n": 20,            # only the N lowest-level members can be flagged for inactivity; 0 = everyone
    "stale_hours": 2,          # stats older than this are flagged as stale
    "level_drop": 0,           # flag when a member's level fell by MORE than this over 90 days
}

# Chat activity colours on the Members page. Each value is the minimum messages for that
# tier; anything below `red` is the lowest tier. The all-time defaults are the 90-day
# defaults times five.
ACTIVITY_DEFAULTS = {
    "d90": {"red": 10, "yellow": 100, "green": 250, "blue": 500, "white": 1000},
    "total": {"red": 50, "yellow": 500, "green": 1250, "blue": 2500, "white": 5000},
}
_ACTIVITY_ORDER = ["red", "yellow", "green", "blue", "white"]

_MAX_LEVEL = 10000

# Versions offered on the panel: 26.1 can be in SkyBlock (needed for .warpout); 1.8.9 is the
# long-stable fallback (config.FALLBACK_VERSION).
MINECRAFT_VERSIONS = ("26.1", "1.8.9")
_cache: dict = {}


def _stored(guild_key: str) -> dict:
    hit = _cache.get(guild_key)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]
    stored = manager.get_guild_config(guild_key) or {"rank_requirements": {}, "attention": {}}
    _cache[guild_key] = (time.time(), stored)
    return stored


def invalidate(guild_key: str) -> None:
    _cache.pop(guild_key, None)


def get_rank_requirements(config) -> dict:
    """{bot_rank_key: level} in rank order (lowest first): the panel's value where one is
    saved, otherwise the built-in value from .env (config.ranks)."""
    overrides = _stored(config.key)["rank_requirements"]
    return {rank: int(overrides.get(rank, default_level)) for rank, default_level in config.ranks.items()}


def get_rank_roles(config) -> dict:
    """{bot_rank_key: discord_role_id} for the ranks that have a Discord role saved on the panel."""
    saved = _stored(config.key).get("rank_roles", {})
    return {rank: int(saved[rank]) for rank in config.ranks if saved.get(rank)}


def get_member_role(config):
    """The panel's "is in this guild" Discord role id, or None."""
    saved = _stored(config.key).get("member_role")
    return int(saved) if saved else None


def validate_member_role(raw):
    raw = str(raw or "").strip()
    if not raw:
        return None
    if not raw.isdigit() or not 17 <= len(raw) <= 20:
        raise ValueError("The guild role must be a Discord role ID (17-20 digits)")
    return int(raw)


def validate_rank_roles(config, values: dict) -> dict:
    """values is {rank: "role id" | ""}; returns {rank: int} without the blanks."""
    unknown = set(values) - set(config.ranks)
    if unknown:
        raise ValueError(f"Unknown rank: {', '.join(sorted(unknown))}")
    result = {}
    for rank, raw in values.items():
        raw = str(raw or "").strip()
        if not raw:
            continue
        if not raw.isdigit() or not 17 <= len(raw) <= 20:
            raise ValueError(f"{rank}: the Discord role must be a role ID (17-20 digits)")
        result[rank] = int(raw)
    ids = list(result.values())
    if len(ids) != len(set(ids)):
        raise ValueError("Each rank needs its own Discord role; two ranks can't share one")
    return result


def get_minecraft_version(config) -> str:
    """The protocol version this guild's bot should connect with: the panel's choice, else
    MINECRAFT_VERSION from .env. Read when the bot is (re)started."""
    from config import VERSION
    saved = manager.get_minecraft_version(config.key)
    return saved if saved in MINECRAFT_VERSIONS else VERSION


def validate_minecraft_version(version) -> str:
    if version not in MINECRAFT_VERSIONS:
        raise ValueError(f"Minecraft version must be one of: {', '.join(MINECRAFT_VERSIONS)}")
    return version


def get_activity_tiers(guild_key: str) -> dict:
    stored = _stored(guild_key).get("activity_tiers", {})
    return {
        period: {k: stored.get(period, {}).get(k, d) for k, d in defaults.items()}
        for period, defaults in ACTIVITY_DEFAULTS.items()
    }


def get_attention_settings(guild_key: str) -> dict:
    stored = _stored(guild_key)["attention"]
    return {k: stored.get(k, default) for k, default in ATTENTION_DEFAULTS.items()}


def validate_ranks(config, ranks: dict) -> dict:
    """Returns the overrides ({rank: int}); raises ValueError with a user-facing message."""
    keys = list(config.ranks.keys())
    unknown = set(ranks) - set(keys)
    if unknown:
        raise ValueError(f"Unknown rank: {', '.join(sorted(unknown))}")
    result = {}
    previous = None
    for rank in keys:
        value = ranks.get(rank, config.ranks[rank])
        if isinstance(value, bool) or not isinstance(value, (int, float)) or int(value) != value:
            raise ValueError(f"{rank}: the level requirement must be a whole number")
        value = int(value)
        if value < 0 or value > _MAX_LEVEL:
            raise ValueError(f"{rank}: the level requirement must be between 0 and {_MAX_LEVEL}")
        if previous is not None and value <= previous:
            raise ValueError(f"{rank}: must be higher than the rank below it ({previous})")
        result[rank] = value
        previous = value
    return result


def validate_activity(values: dict) -> dict:
    """values is {"d90": {tier: n}, "total": {tier: n}}; missing tiers fall back to the defaults."""
    unknown = set(values) - set(ACTIVITY_DEFAULTS)
    if unknown:
        raise ValueError(f"Unknown activity period: {', '.join(sorted(unknown))}")
    result = {}
    for period, defaults in ACTIVITY_DEFAULTS.items():
        given = values.get(period, {})
        bad = set(given) - set(defaults)
        if bad:
            raise ValueError(f"Unknown activity tier: {', '.join(sorted(bad))}")
        merged = {k: given.get(k, d) for k, d in defaults.items()}
        previous = 0
        for k in _ACTIVITY_ORDER:
            v = merged[k]
            if isinstance(v, bool) or not isinstance(v, (int, float)) or int(v) != v:
                raise ValueError(f"{k}: must be a whole number")
            merged[k] = int(v)
            if merged[k] <= previous:
                raise ValueError("Message tiers must increase from red up to white, starting at 1 or more")
            previous = merged[k]
        if merged["white"] > 10_000_000:
            raise ValueError("The top tier can be at most 10,000,000 messages")
        result[period] = merged
    return result


def validate_attention(values: dict) -> dict:
    unknown = set(values) - set(ATTENTION_DEFAULTS)
    if unknown:
        raise ValueError(f"Unknown setting: {', '.join(sorted(unknown))}")
    merged = {k: values.get(k, d) for k, d in ATTENTION_DEFAULTS.items()}
    for k, v in merged.items():
        if isinstance(v, bool) or not isinstance(v, (int, float)) or int(v) != v:
            raise ValueError(f"{k}: must be a whole number")
        merged[k] = int(v)
    if not 1 <= merged["low_activity_days"] < merged["inactive_days"] < merged["kick_risk_days"] <= 3650:
        raise ValueError("Days must increase: low activity, then inactive, then kick risk (at most 3650)")
    if not 0 <= merged["bottom_n"] <= 1000:
        raise ValueError("Members checked must be between 0 and 1000")
    if not 1 <= merged["stale_hours"] <= 720:
        raise ValueError("Stale stats hours must be between 1 and 720")
    if not 0 <= merged["level_drop"] <= 1000:
        raise ValueError("Level drop must be between 0 and 1000")
    return merged
