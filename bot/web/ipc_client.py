"""Shared HTTP client for the panel process (web_main.py) to reach the bot
process's internal IPC API (bot_ipc.py), running on BOT_IPC_URL.

Two failure-handling shapes are needed by callers:
- ipc_get(): swallow any failure and return None — used by routes that fall
  back to an "offline" placeholder rather than erroring (bot status, overview).
- ipc_get_or_raise() / ipc_post_or_raise(): surface failures as HTTPException
  (503 if the bot process is unreachable, resp.status on a non-200 reply) —
  used by routes with no sensible offline fallback (members, restart, stop).
"""
import os

import aiohttp
from fastapi import HTTPException

IPC_URL = os.getenv("BOT_IPC_URL", "http://localhost:8081")
IPC_SECRET = os.getenv("BOT_IPC_SECRET", "")
TIMEOUT = aiohttp.ClientTimeout(total=5)
LONG_TIMEOUT = aiohttp.ClientTimeout(total=15)


def ipc_headers() -> dict:
    return {"X-IPC-Secret": IPC_SECRET} if IPC_SECRET else {}


async def ipc_get(path: str, timeout: aiohttp.ClientTimeout = TIMEOUT):
    """GET path (appended to IPC_URL). Returns the parsed JSON body on HTTP
    200, else None — covers both network failures and non-200 responses."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{IPC_URL}{path}", headers=ipc_headers(), timeout=timeout) as resp:
                if resp.status == 200:
                    return await resp.json()
    except Exception:
        pass
    return None


async def ipc_get_or_raise(path: str, timeout: aiohttp.ClientTimeout = LONG_TIMEOUT):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{IPC_URL}{path}", headers=ipc_headers(), timeout=timeout) as resp:
                if resp.status == 200:
                    return await resp.json()
                raise HTTPException(status_code=resp.status, detail="IPC error")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=503, detail="Bot process is offline")


async def ipc_post_or_raise(path: str, timeout: aiohttp.ClientTimeout = LONG_TIMEOUT):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{IPC_URL}{path}", headers=ipc_headers(), timeout=timeout) as resp:
                if resp.status == 200:
                    return await resp.json()
                raise HTTPException(status_code=resp.status, detail="IPC error")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=503, detail="Bot process is offline")
