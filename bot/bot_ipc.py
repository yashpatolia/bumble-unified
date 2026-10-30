import asyncio
import base64
import binascii
import datetime
import logging
import os
import re
import time as _time

import discord
from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel
from db import manager
from lib.guild_list import parse_guild_list as _parse_guild_list, parse_online_igns as _parse_online_igns

_IPC_SECRET = os.getenv("BOT_IPC_SECRET", "")
_IGN_RE = re.compile(r"^[A-Za-z0-9_]{3,16}$")


class _KickBody(BaseModel):
    ign: str
    reason: str = ""
    actor: str = "panel"


class _InviteBody(BaseModel):
    ign: str
    actor: str = "panel"


class _SyncRolesBody(BaseModel):
    uuid: str = ""       # sync just this member...
    guild_key: str = ""  # ...or every linked member of this guild


class _EmojiBody(BaseModel):
    name: str
    image: str  # base64 of the PNG/JPG/GIF file


def _clean_reason(reason: str) -> str:
    """Single line, no control characters, capped, so it can never smuggle a second command."""
    cleaned = re.sub(r"[\x00-\x1f\x7f]", " ", reason).strip()[:100]
    return cleaned or "Removed via panel"


def _verify(request: Request):
    if _IPC_SECRET and request.headers.get("X-IPC-Secret") != _IPC_SECRET:
        raise HTTPException(status_code=403)


def _last_3_month_keys() -> list:
    """Current UTC month plus the previous 2, as '%Y-%m' keys — a ~90-day approximation."""
    now = datetime.datetime.utcnow().replace(day=1)
    keys = []
    for _ in range(3):
        keys.append(now.strftime('%Y-%m'))
        now = (now - datetime.timedelta(days=1)).replace(day=1)
    return keys


def _member_dict(r, online, msg_counts, old_levels, lifetime_counts, excused, bot_names) -> dict:
    ign, level = r[0], r[2]
    old = old_levels.get(ign)
    level_gain_90d = None
    level_gain_days = None
    if level is not None and old is not None:
        old_level, old_recorded_at = old
        level_gain_90d = level - old_level
        level_gain_days = (int(_time.time()) - old_recorded_at) // 86400
    return {
        "ign": ign, "rank": r[1], "skyblock_level": level, "last_login": r[3], "uuid": r[4] or None,
        "discord_name": r[5] or None, "discord_id": str(r[6]) if r[6] else None, "discord_avatar": r[7] or None,
        "stats_fetched_at": r[8], "online": online, "messages_90d": msg_counts.get(r[4], 0), "messages_total": lifetime_counts.get(r[4], 0), "excused": excused.get(ign.lower()), "is_bot": ign.lower() in bot_names,
        "level_gain_90d": level_gain_90d, "level_gain_days": level_gain_days,
    }


def create_ipc_app(client):
    app = FastAPI(docs_url=None, redoc_url=None)
    # The guilds' own bot accounts sit in the roster but are not real players (excluded from averages).
    bot_names = {c.mc_username.lower() for c in client.guild_configs.values()}

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
            msg_counts = manager.get_message_counts_90d(key, _last_3_month_keys())
            lifetime = manager.get_message_counts_lifetime(key)
            old_levels = manager.get_level_gain_90d(key)
            excused = manager.get_excused(key)
            members = [_member_dict(r, False, msg_counts, old_levels, lifetime, excused, bot_names) for r in rows]
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
        msg_counts = manager.get_message_counts_90d(key, _last_3_month_keys())
        lifetime = manager.get_message_counts_lifetime(key)
        old_levels = manager.get_level_gain_90d(key)
        excused = manager.get_excused(key)
        members = [_member_dict(r, r[0] in online_igns, msg_counts, old_levels, lifetime, excused, bot_names) for r in rows]
        members.sort(key=lambda m: (not m["online"], m["ign"].lower()))
        return {"members": members}

    async def _audit(state, text: str) -> None:
        """Mirror panel actions into the guild's Discord logs channel so they are never silent."""
        logging.info(f"[panel] {text}")
        if state.logs:
            try:
                await asyncio.to_thread(state.logs.send, embed=discord.Embed(colour=discord.Colour.blurple(), description=f"Panel: {text}"))
            except Exception as e:
                logging.warning(f"[panel] could not post audit log: {e}")

    def _ready_state(key: str):
        if key not in client.guild_configs:
            raise HTTPException(status_code=404, detail="Unknown guild key")
        state = client.guilds_state[key]
        if not state.connected or not state.bot:
            raise HTTPException(status_code=503, detail="The bot is not connected to Minecraft right now")
        return state

    @app.post("/guild/{key}/kick", dependencies=[Depends(_verify)])
    async def kick_member(key: str, body: _KickBody):
        state = _ready_state(key)
        ign = body.ign.strip()
        if not _IGN_RE.match(ign):
            raise HTTPException(status_code=400, detail="That is not a valid Minecraft username")
        if ign.lower() == client.guild_configs[key].mc_username.lower():
            raise HTTPException(status_code=400, detail="The bot cannot kick itself")
        if not any(r[0].lower() == ign.lower() for r in manager.get_guild_members(key)):
            raise HTTPException(status_code=404, detail=f"{ign} is not in this guild's roster")
        reason = _clean_reason(body.reason)
        state.bot.chat(f"/guild kick {ign} {reason}")
        await _audit(state, f"**{body.actor}** kicked `{ign}` ({reason})")
        return {"status": "sent", "ign": ign}

    @app.post("/guild/{key}/invite", dependencies=[Depends(_verify)])
    async def invite_player(key: str, body: _InviteBody):
        state = _ready_state(key)
        ign = body.ign.strip()
        if not _IGN_RE.match(ign):
            raise HTTPException(status_code=400, detail="That is not a valid Minecraft username")
        state.guild_invite = None
        state.bot.chat(f"/guild invite {ign}")
        await asyncio.sleep(1.5)
        reply = state.guild_invite
        state.guild_invite = None
        await _audit(state, f"**{body.actor}** invited `{ign}`")
        return {"status": "sent", "ign": ign, "message": reply or "Invite sent. Hypixel has not replied yet."}

    @app.post("/restart/{key}", dependencies=[Depends(_verify)])
    async def restart_bot(key: str):
        from cogs.bridge.connections import reload_bridge_cogs

        if key not in client.guild_configs:
            raise HTTPException(status_code=404, detail="Unknown bot key")
        # A manual restart picks up the panel's version choice, even after an automatic fallback.
        from lib.guild_settings import get_minecraft_version
        state = client.guilds_state[key]
        state.version = get_minecraft_version(client.guild_configs[key])
        state.recent_disconnects.clear()
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

    @app.get("/roles", dependencies=[Depends(_verify)])
    async def list_roles():
        """Discord roles the bot could hand out, for the rank-role pickers on the Config page."""
        roles = []
        for server in client.guilds:
            top = server.me.top_role if server.me else None
            for role in sorted(server.roles, key=lambda r: r.position, reverse=True):
                if role.is_default() or role.managed:
                    continue
                roles.append({
                    "id": str(role.id), "name": role.name, "server": server.name,
                    "color": f"{role.color.value:06x}" if role.color.value else None,
                    "assignable": bool(top and role < top),
                })
        return {"roles": roles}

    @app.post("/sync-roles", dependencies=[Depends(_verify)])
    async def sync_roles(body: _SyncRolesBody):
        """Re-applies guild rank roles for one member, or in the background for a whole guild."""
        from lib.role_sync import sync_member_roles

        if body.uuid:
            await sync_member_roles(client, body.uuid)
            return {"status": "synced"}
        if body.guild_key not in client.guild_configs:
            raise HTTPException(status_code=404, detail="Unknown guild key")

        async def run():
            for row in manager.get_guild_members(body.guild_key):
                if row[4] and row[6]:  # has a uuid and a linked Discord account
                    await sync_member_roles(client, row[4])
                    await asyncio.sleep(0.3)  # stay clear of Discord's rate limits

        asyncio.create_task(run())
        return {"status": "started"}

    @app.get("/emojis", dependencies=[Depends(_verify)])
    async def list_emojis():
        """The bot's application emojis (what POST /emojis creates), for the dye catalog picker."""
        try:
            emojis = await client.fetch_application_emojis()
        except discord.HTTPException as exc:
            raise HTTPException(status_code=502, detail=f"Discord refused: {exc.text or exc}")
        return {"emojis": sorted(
            ({"id": str(e.id), "name": e.name, "animated": e.animated} for e in emojis),
            key=lambda e: e["name"].lower(),
        )}

    @app.post("/emojis", dependencies=[Depends(_verify)])
    async def upload_emoji(body: _EmojiBody):
        """Uploads a new application emoji (usable anywhere the bot sends messages)."""
        try:
            image = base64.b64decode(body.image, validate=True)
        except (binascii.Error, ValueError):
            raise HTTPException(status_code=400, detail="Image is not valid base64")
        try:
            emoji = await client.create_application_emoji(name=body.name, image=image)
        except discord.HTTPException as exc:
            raise HTTPException(status_code=400, detail=f"Discord refused the emoji: {exc.text or exc}")
        return {"id": str(emoji.id), "name": emoji.name, "animated": emoji.animated}

    @app.get("/api-usage", dependencies=[Depends(_verify)])
    def get_api_usage():
        return manager.get_api_call_counts()

    return app
