import os

from fastapi import Depends, FastAPI, HTTPException, Request

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
