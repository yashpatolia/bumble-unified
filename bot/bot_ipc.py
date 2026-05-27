import asyncio
import os
import re

from fastapi import Depends, FastAPI, HTTPException, Request

_IPC_SECRET = os.getenv("BOT_IPC_SECRET", "")


def _verify(request: Request):
    if _IPC_SECRET and request.headers.get("X-IPC-Secret") != _IPC_SECRET:
        raise HTTPException(status_code=403)


def _parse_members(lines: list) -> list:
    members = []
    for line in lines:
        line = line.strip()
        if not line or ":" in line or line.startswith("-"):
            continue
        m = re.match(r"^\[([^\]]+)\]\s+(\w+)(.*?)$", line)
        if m:
            members.append({
                "rank": m.group(1),
                "ign": m.group(2),
                "online": "●" in m.group(3) or "•" in m.group(3),
            })
    return members


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
            raise HTTPException(status_code=503, detail="Bot offline")
        state.guild_list.clear()
        state.bot.chat("/guild list")
        await asyncio.sleep(1.0)
        members = _parse_members(list(state.guild_list))
        state.guild_member_count = len(members)
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
