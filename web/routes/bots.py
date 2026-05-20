from fastapi import APIRouter, Depends, HTTPException, Request

from web.auth import require_admin, require_bot_control

router = APIRouter(prefix="/api/bots", tags=["bots"])


def _client(request: Request):
    return request.app.state.client


@router.get("")
def get_bots(request: Request, _=Depends(require_bot_control)):
    client = _client(request)
    result = {}
    for key, config in client.guild_configs.items():
        state = client.guilds_state[key]
        connected = False
        if state.bot:
            try:
                # Mineflayer bot exposes `ended` when disconnected
                connected = not getattr(state.bot, "ended", True)
            except Exception:
                connected = False
        result[key] = {
            "key": key,
            "name": config.display_name,
            "short_name": config.short_name,
            "username": config.mc_username,
            "connected": connected,
        }
    return result


@router.post("/{key}/restart")
async def restart_bot(key: str, request: Request, _=Depends(require_bot_control)):
    client = _client(request)
    if key not in client.guild_configs:
        raise HTTPException(status_code=404, detail="Unknown bot key")
    await client.start_mineflayer(restart=True, account=key)
    return {"status": "restarting", "key": key}


@router.post("/{key}/stop")
def stop_bot(key: str, request: Request, _=Depends(require_bot_control)):
    client = _client(request)
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
