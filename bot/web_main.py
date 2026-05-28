import asyncio
import logging
import os

import uvicorn

from config import PANEL_PORT
from db import manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(filename)s:%(lineno)d | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


async def run_web():
    from db.migrate import run_migrations
    run_migrations(os.getenv("DATABASE_URL", ""))

    from web.logs import WebLogHandler
    logging.getLogger().addHandler(WebLogHandler())

    from web.app import create_app
    web_app = create_app()
    config = uvicorn.Config(web_app, host="0.0.0.0", port=PANEL_PORT, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()


asyncio.run(run_web())
