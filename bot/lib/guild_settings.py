"""Panel-editable guild settings, merged over the built-in defaults.

Rank level requirements default to the env-driven values in config.py (GuildConfig.ranks);
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
    """{bot_rank_key: level} in rank order (lowest first). The lowest rank keeps its built-in
    value because it is the default rank; only the higher ranks can be overridden."""
    overrides = _stored(config.key)["rank_requirements"]
    merged = {}
    for i, (rank, default_level) in enumerate(config.ranks.items()):
        merged[rank] = default_level if i == 0 else int(overrides.get(rank, default_level))
    return merged


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
    """Returns the editable overrides ({rank: int}); raises ValueError with a user-facing message."""
    keys = list(config.ranks.keys())
    editable = keys[1:]
    unknown = set(ranks) - set(editable)
    if unknown:
        raise ValueError(f"Unknown or non-editable rank: {', '.join(sorted(unknown))}")
    result = {}
    previous = config.ranks[keys[0]]
    for rank in editable:
        value = ranks.get(rank, config.ranks[rank])
        if isinstance(value, bool) or not isinstance(value, (int, float)) or int(value) != value:
            raise ValueError(f"{rank}: the level requirement must be a whole number")
        value = int(value)
        if value < 0 or value > _MAX_LEVEL:
            raise ValueError(f"{rank}: the level requirement must be between 0 and {_MAX_LEVEL}")
        if value <= previous:
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
