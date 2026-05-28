import asyncio
import os
import re

from fastapi import Depends, FastAPI, HTTPException, Request
from db import manager

_IPC_SECRET = os.getenv("BOT_IPC_SECRET", "")


def _verify(request: Request):
    if _IPC_SECRET and request.headers.get("X-IPC-Secret") != _IPC_SECRET:
        raise HTTPException(status_code=403)


_RANK_HEADER = re.compile(r"^-+\s+(.+?)\s+-+$")
_IGN_RE = re.compile(r"(?:\[[\w+]+\]\s+)?([A-Za-z0-9_]{3,16})")
_SKIP_WORDS = {"Guild", "Total", "Online", "Members", "The"}


def _parse_guild_list(lines: list) -> list:
    """Parse /guild list lines into [{ign, rank}] using section headers for guild rank."""
    members = []
    current_rank = ""
    for line in lines:
        line = line.strip()
        if not line or ":" in line:
            continue
        m = _RANK_HEADER.match(line)
        if m:
            current_rank = m.group(1).strip()
            continue
        # Strip MC rank prefixes and bullet chars, then extract IGNs
        clean = re.sub(r"\[[\w+]+\]", "", line).replace("●", "").replace("•", "")
        for token in clean.split():
            if re.match(r"^[A-Za-z0-9_]{3,16}$", token) and token not in _SKIP_WORDS:
                members.append({"ign": token, "rank": current_rank})
    return members


def _parse_online_igns(lines: list) -> set:
    """Parse /guild online lines into a set of online IGNs."""
    online = set()
    for line in lines:
        line = line.strip()
        if not line or ":" in line or "--" in line:
            continue
        clean = re.sub(r"\[[\w+]+\]", "", line).replace("●", "").replace("•", "")
        for token in clean.split():
            if re.match(r"^[A-Za-z0-9_]{3,16}$", token) and token not in _SKIP_WORDS:
                online.add(token)
    return online


def create_ipc_app(client):
    app = FastAPI(docs_url=None, redoc_url=None)

    @app.get("/status", dependencies=[Depends(_verify)])
    def get_status():
        return {
            key: {
                "key": key,
                "name": config.display_name,
                "short_name": config.short_name,
                "username": config.mc_username,
                "connected": client.guilds_state[key].connected,
            }
            for key, config in client.guild_configs.items()
        }

    @app.get("/guild/{key}/overview", dependencies=[Depends(_verify)])
    def get_guild_overview(key: str):
        if key not in client.guild_configs:
            raise HTTPException(status_code=404, detail="Unknown guild key")
        config = client.guild_configs[key]
        state = client.guilds_state[key]
        return {
            "key": key,
            "name": config.display_name,
            "short_name": config.short_name,
            "username": config.mc_username,
            "connected": state.connected,
            "member_count": state.guild_member_count,
            "recent_chat": list(state.recent_chat),
            "recent_events": list(state.recent_events),
        }

    @app.get("/guild/{key}/members", dependencies=[Depends(_verify)])
    async def get_guild_members(key: str):
        if key not in client.guild_configs:
            raise HTTPException(status_code=404, detail="Unknown guild key")
        state = client.guilds_state[key]

        if not state.connected or not state.bot:
            # Return DB cache with everyone offline
            rows = manager.get_guild_members(key)
            members = [{"ign": r[0], "rank": r[1], "online": False} for r in rows]
            return {"members": sorted(members, key=lambda m: m["ign"].lower())}

        # Refresh DB from /guild list
        state.guild_list.clear()
        state.save_guild_list = True
        state.bot.chat("/guild list")
        await asyncio.sleep(1.5)

        parsed = _parse_guild_list(list(state.guild_list))
        if parsed:
            manager.sync_guild_members(key, parsed)
            state.guild_member_count = len(parsed)

        # Get online members via /guild online
        state.guild_online.clear()
        state.save_guild_online = True
        state.bot.chat("/guild online")
        await asyncio.sleep(1.5)
        state.save_guild_online = False

        online_igns = _parse_online_igns(list(state.guild_online))

        rows = manager.get_guild_members(key)
        members = [{"ign": r[0], "rank": r[1], "online": r[0] in online_igns} for r in rows]
        members.sort(key=lambda m: (not m["online"], m["ign"].lower()))
        return {"members": members}

    @app.post("/restart/{key}", dependencies=[Depends(_verify)])
    async def restart_bot(key: str):
        if key not in client.guild_configs:
            raise HTTPException(status_code=404, detail="Unknown bot key")
        await client.start_mineflayer(restart=True, account=key)
        return {"status": "restarting", "key": key}

    @app.post("/stop/{key}", dependencies=[Depends(_verify)])
    def stop_bot(key: str):
        if key not in client.guild_configs:
            raise HTTPException(status_code=404, detail="Unknown bot key")
        state = client.guilds_state[key]
        if state.bot:
            state.manual_stop = True
            try:
                state.bot.end()
            except Exception:
                state.manual_stop = False
                raise HTTPException(status_code=500, detail="Failed to stop bot")
        return {"status": "stopped", "key": key}

    return app
