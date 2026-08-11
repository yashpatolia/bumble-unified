import asyncio
import os

from fastapi import Depends, FastAPI, HTTPException, Request
from db import manager
from lib.guild_list import parse_guild_list as _parse_guild_list, parse_online_igns as _parse_online_igns

_IPC_SECRET = os.getenv("BOT_IPC_SECRET", "")


def _verify(request: Request):
    if _IPC_SECRET and request.headers.get("X-IPC-Secret") != _IPC_SECRET:
        raise HTTPException(status_code=403)


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
        }

    @app.get("/guild/{key}/members", dependencies=[Depends(_verify)])
    async def get_guild_members(key: str):
        if key not in client.guild_configs:
            raise HTTPException(status_code=404, detail="Unknown guild key")
        state = client.guilds_state[key]

        if not state.connected or not state.bot:
            # Return DB cache with everyone offline
            rows = manager.get_guild_members(key)
            members = [{"ign": r[0], "rank": r[1], "skyblock_level": r[2], "last_login": r[3], "uuid": r[4] or None, "discord_name": r[5] or None, "discord_id": str(r[6]) if r[6] else None, "discord_avatar": r[7] or None, "stats_fetched_at": r[8], "online": False} for r in rows]
            return {"members": sorted(members, key=lambda m: m["ign"].lower())}

        # Refresh DB from /guild list. Serialized with the Discord
        # /guild list|online commands via state.list_lock so the two
        # can't interleave and bleed unrelated chat into each other's
        # shared guild_list/guild_online buffers.
        async with state.list_lock:
            state.guild_list.clear()
            state.save_guild_list = True
            state.bot.chat("/guild list")
            await asyncio.sleep(1.5)
            state.save_guild_list = False

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
        members = [{"ign": r[0], "rank": r[1], "skyblock_level": r[2], "last_login": r[3], "uuid": r[4] or None, "discord_name": r[5] or None, "discord_id": str(r[6]) if r[6] else None, "discord_avatar": r[7] or None, "stats_fetched_at": r[8], "online": r[0] in online_igns} for r in rows]
        members.sort(key=lambda m: (not m["online"], m["ign"].lower()))
        return {"members": members}

    @app.post("/restart/{key}", dependencies=[Depends(_verify)])
    async def restart_bot(key: str):
        from cogs.bridge.connections import reload_bridge_cogs

        if key not in client.guild_configs:
            raise HTTPException(status_code=404, detail="Unknown bot key")
        await client.start_mineflayer(account=key)
        await reload_bridge_cogs(client, client.guild_configs[key])
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

    @app.get("/api-usage", dependencies=[Depends(_verify)])
    def get_api_usage():
        return manager.get_api_call_counts()

    return app
