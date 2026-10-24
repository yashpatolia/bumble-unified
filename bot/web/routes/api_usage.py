"""Combined local + live Hypixel API usage view. Read-only, so any signed-in viewer can see it."""
import time

from fastapi import APIRouter, Depends

from db import manager
from web.auth import require_auth

router = APIRouter(prefix="/api/bots", tags=["bots"])

# Everyone viewing the Admin page polls this, and it makes a live Hypixel call, so
# one shared copy is reused for a short while instead of one call per viewer.
_CACHE_SECONDS = 30
_cache: tuple = (0.0, None)


@router.get("/api-usage")
async def get_api_usage(_=Depends(require_auth)):
    """Return local API call counts plus live Hypixel key info."""
    global _cache
    if _cache[1] is None or time.time() - _cache[0] > _CACHE_SECONDS:
        from lib.hypixel import fetch_key_info
        counts = manager.get_api_call_counts()
        hypixel = await fetch_key_info()
        _cache = (time.time(), {
            "local": counts,
            "hypixel": hypixel,
            "rate_limit": {"requests": 300, "window_minutes": 5},
        })
    return _cache[1]
