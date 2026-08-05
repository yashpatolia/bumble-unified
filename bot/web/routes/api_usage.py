"""Combined local + live Hypixel API usage view for the owner."""
from fastapi import APIRouter, Depends

from db import manager
from web.auth import require_owner

router = APIRouter(prefix="/api/bots", tags=["bots"])


@router.get("/api-usage")
async def get_api_usage(_=Depends(require_owner)):
    """Return local API call counts plus live Hypixel key info."""
    from lib.hypixel import fetch_key_info
    counts = manager.get_api_call_counts()
    hypixel = await fetch_key_info()
    return {
        "local": counts,
        "hypixel": hypixel,
        "rate_limit": {"requests": 300, "window_minutes": 5},
    }
