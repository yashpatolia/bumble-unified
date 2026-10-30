"""Read-only guild data: live overview/members (proxied to the bot process's
IPC API), plus the message-count leaderboard and online-activity graph
(DB-only, no IPC involved)."""
import datetime
import time

from fastapi import APIRouter, Depends, HTTPException

from config import GUILD_CONFIGS
from lib import guild_settings
from lib.censor import censor
from lib.levels import catacombs_level
from db import manager
from web.auth import is_guest, require_auth
from web.ipc_client import ipc_get, ipc_get_or_raise, LONG_TIMEOUT

router = APIRouter(prefix="/api/bots", tags=["bots"])


@router.get("/{key}/overview")
async def get_guild_overview(key: str, _=Depends(require_auth)):
    if key not in GUILD_CONFIGS:
        raise HTTPException(status_code=404, detail="Unknown guild key")
    overview = await ipc_get(f"/guild/{key}/overview")
    if overview is not None:
        # Chat is censored here, in the panel process, so no viewer ever receives the raw text.
        overview["recent_chat"] = [{**m, "message": censor(m.get("message", ""))} for m in overview.get("recent_chat", [])]
        return overview
    config = GUILD_CONFIGS[key]
    return {
        "key": key,
        "name": config.display_name,
        "short_name": config.short_name,
        "username": config.mc_username,
        "connected": False,
        "member_count": 0,
        "recent_chat": [],
        "recent_events": [],
    }


# Loading members makes the bot run /guild list in-game. Guests are anonymous, so
# they share one short-lived cached copy instead of each triggering an in-game refresh.
_GUEST_MEMBERS_TTL = 120
_guest_members_cache: dict = {}


def _strip_discord_ids(members: list) -> list:
    """Guests get no Discord IDs and no private excuse notes (only that someone is excused)."""
    return [
        {**m, "discord_id": None, "excused": {**m["excused"], "reason": None, "by": None} if m.get("excused") else None}
        for m in members
    ]


@router.get("/{key}/members")
async def get_guild_members(key: str, claims=Depends(require_auth)):
    if key not in GUILD_CONFIGS:
        raise HTTPException(status_code=404, detail="Unknown guild key")
    if not is_guest(claims):
        return await ipc_get_or_raise(f"/guild/{key}/members", timeout=LONG_TIMEOUT)
    hit = _guest_members_cache.get(key)
    if not hit or time.time() - hit[0] > _GUEST_MEMBERS_TTL:
        data = await ipc_get_or_raise(f"/guild/{key}/members", timeout=LONG_TIMEOUT)
        hit = (time.time(), {"members": _strip_discord_ids(data.get("members", []))})
        _guest_members_cache[key] = hit
    return hit[1]


@router.get("/{key}/activity")
async def get_activity(key: str, hours: int = 24, _=Depends(require_auth)):
    if key not in GUILD_CONFIGS:
        raise HTTPException(status_code=404, detail="Unknown guild key")
    hours = max(1, min(hours, 168))
    rows = manager.get_online_activity(key, hours)
    return {"points": [{"t": r[0].isoformat(), "online": r[1]} for r in rows]}


@router.get("/{key}/level-trend")
async def get_level_trend(key: str, days: int = 30, _=Depends(require_auth)):
    if key not in GUILD_CONFIGS:
        raise HTTPException(status_code=404, detail="Unknown guild key")
    days = max(7, min(days, 90))
    # The guilds' bot accounts are in the roster but are not real players, so they stay out of the average.
    bots = tuple(c.mc_username for c in GUILD_CONFIGS.values())
    rows = manager.get_average_level_trend(key, days, exclude_igns=bots)
    return {"points": [{"t": datetime.datetime.utcfromtimestamp(r[0]).strftime("%Y-%m-%d"), "avg": round(r[1], 2), "members": r[2]} for r in rows]}


@router.get("/{key}/level-leaderboard")
async def get_level_leaderboard(key: str, days: int = 30, claims=Depends(require_auth)):
    """Top levels right now, plus who gained the most levels over the last `days` days."""
    if key not in GUILD_CONFIGS:
        raise HTTPException(status_code=404, detail="Unknown guild key")
    days = days if days in (7, 30, 90) else 30
    now = int(time.time())
    anchors = {ign.lower(): v for ign, v in manager.get_level_gains(key, days).items()}
    guest = is_guest(claims)
    people = []
    for r in manager.get_guild_members(key):
        ign, rank, level, uuid = r[0], r[1], r[2], r[4] or None
        if level is None:
            continue
        anchor = anchors.get(ign.lower())
        gain = days_covered = None
        if anchor is not None:
            gain = round(level - anchor[0], 2)
            days_covered = max(0, (now - anchor[1]) // 86400)
        people.append({"ign": ign, "rank": rank, "level": level, "uuid": uuid, "discord_name": r[5] or None,
                       "discord_avatar": r[7] or None, "gain": gain, "days_covered": days_covered})
    top = sorted(people, key=lambda p: p["level"], reverse=True)[:50]
    climbers = sorted((p for p in people if p["gain"] is not None and p["gain"] > 0), key=lambda p: p["gain"], reverse=True)[:50]
    return {"days": days, "top": top, "climbers": climbers}


@router.get("/{key}/leaderboard")
async def get_leaderboard(key: str, period: str = "lifetime", claims=Depends(require_auth)):
    if key not in GUILD_CONFIGS:
        raise HTTPException(status_code=404, detail="Unknown guild key")
    now = datetime.datetime.utcnow()
    if period == "month":
        period_key = now.strftime('%Y-%m')
    elif period == "week":
        period_key = now.strftime('%G-W%V')
    else:
        period = "lifetime"
        period_key = ""
    rows = manager.get_message_leaderboard(key, period, period_key)
    return {"leaderboard": [
        {"ign": r[0], "count": r[1], "uuid": r[2] or None, "discord_name": r[3] or None, "discord_id": None if is_guest(claims) else (str(r[4]) if r[4] else None), "discord_avatar": r[5] or None}
        for r in rows
    ]}


def _last_3_month_keys() -> list:
    """Current UTC month plus the previous 2: a ~90-day approximation, same as the members list."""
    now = datetime.datetime.utcnow().replace(day=1)
    keys = []
    for _ in range(3):
        keys.append(now.strftime("%Y-%m"))
        now = (now - datetime.timedelta(days=1)).replace(day=1)
    return keys


@router.get("/{key}/members/{ign}")
async def get_member_detail(key: str, ign: str, claims=Depends(require_auth)):
    """Everything on one member's page: current stats, rank progress, chat activity, dyes and the
    daily level / Catacombs / slayer history (up to 90 days)."""
    if key not in GUILD_CONFIGS:
        raise HTTPException(status_code=404, detail="Unknown guild key")
    row = manager.get_member_row(key, ign)
    if not row:
        raise HTTPException(status_code=404, detail=f"{ign} is not in this guild's roster")
    ign, rank, level, last_login, uuid, discord_name, discord_id, discord_avatar, fetched_at = row
    uuid = uuid or None
    config = GUILD_CONFIGS[key]
    guest = is_guest(claims)

    ranks = guild_settings.get_rank_requirements(config)
    labels = {bot_rank: hypixel_rank for hypixel_rank, bot_rank in config.discord_rank_map.items()}
    order = list(ranks)
    current = config.discord_rank_map.get(rank)
    next_rank = None
    if current in ranks and order.index(current) + 1 < len(order):
        nxt = order[order.index(current) + 1]
        next_rank = {"label": labels.get(nxt, nxt), "level": ranks[nxt]}

    messages_90d = messages_total = dyes_owned = None
    if uuid:
        messages_90d = manager.get_message_counts_90d(key, _last_3_month_keys()).get(uuid, 0)
        messages_total = manager.get_message_counts_lifetime(key).get(uuid, 0)
        dyes_owned = len(manager.get_unlocked_dyes(uuid))

    history = []
    for recorded_at, lvl, cata_xp, slayer in manager.get_member_history(key, ign, 90, uuid):
        slayer = slayer or None
        history.append({
            "t": datetime.datetime.utcfromtimestamp(recorded_at).strftime("%Y-%m-%d"),
            "level": lvl,
            "catacombs_xp": cata_xp,
            "catacombs_level": catacombs_level(cata_xp) if cata_xp is not None else None,
            "slayer": slayer,
            "slayer_total": sum(slayer.values()) if slayer else None,
        })

    events = []
    for occurred_at, event_guild, event_ign, kind, detail in manager.get_member_events(key, ign, uuid):
        event_config = GUILD_CONFIGS.get(event_guild)
        events.append({
            "t": occurred_at.isoformat(), "guild": event_config.short_name if event_config else event_guild,
            "kind": kind, "ign": event_ign, "detail": detail or {},
        })
    joined = next((e for e in events if e["kind"] == "joined" and e["guild"] == config.short_name), None)
    first_seen = manager.get_member_first_seen(key, ign, uuid)

    excused = manager.get_excused(key).get(ign.lower())
    if excused and guest:
        excused = {**excused, "reason": None, "by": None}
    return {
        "ign": ign, "rank": rank, "uuid": uuid, "level": level,
        "last_login": last_login, "stats_fetched_at": fetched_at,
        "discord": {"name": discord_name, "avatar": discord_avatar, "id": None if guest or not discord_id else str(discord_id)} if discord_name else None,
        "next_rank": next_rank,
        "messages_90d": messages_90d, "messages_total": messages_total,
        "dyes_owned": dyes_owned, "dyes_total": len(manager.get_all_dyes()),
        "excused": excused,
        "history": history,
        "events": events,
        "joined_at": joined["t"] if joined else None,
        "tracked_since": datetime.datetime.utcfromtimestamp(first_seen).strftime("%Y-%m-%d") if first_seen else None,
    }
