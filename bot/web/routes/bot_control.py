"""Bot process lifecycle: connection status, restart, stop — all proxied to
the bot process's internal IPC API via web/ipc_client.py."""
from fastapi import APIRouter, Depends, HTTPException

from config import GUILD_CONFIGS
from web.auth import require_bot_control
from web.ipc_client import ipc_get, ipc_post_or_raise

router = APIRouter(prefix="/api/bots", tags=["bots"])


def _offline_status():
    return {
        key: {
            "key": key,
            "name": config.display_name,
            "short_name": config.short_name,
            "username": config.mc_username,
            "connected": False,
        }
        for key, config in GUILD_CONFIGS.items()
    }


@router.get("")
async def get_bots(_=Depends(require_bot_control)):
    status = await ipc_get("/status")
    return status if status is not None else _offline_status()


@router.post("/{key}/restart")
async def restart_bot(key: str, _=Depends(require_bot_control)):
    if key not in GUILD_CONFIGS:
        raise HTTPException(status_code=404, detail="Unknown bot key")
    return await ipc_post_or_raise(f"/restart/{key}")


@router.post("/{key}/stop")
async def stop_bot(key: str, _=Depends(require_bot_control)):
    if key not in GUILD_CONFIGS:
        raise HTTPException(status_code=404, detail="Unknown bot key")
    return await ipc_post_or_raise(f"/stop/{key}")
