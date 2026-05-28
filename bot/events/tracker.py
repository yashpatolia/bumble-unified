"""
Background bingo tracker — polls Hypixel every 15 minutes for all members of
active bingo events and updates their per-task progress in bingo_progress.

Designed to survive bot restarts: all state is in PostgreSQL, not in memory.
The tracker reads active events from the DB on each cycle so new events are
picked up automatically and ended events are ignored without any code changes.

Rate limit: Hypixel allows 300 API calls / 5 minutes (~1/s).
We sleep _SLEEP_BETWEEN_CALLS seconds between each player fetch, which keeps
us well within budget even for large combined-guild events (~125 members = ~125
calls, completed in ~2.5 minutes at 1.2 s/call).
"""
import asyncio
import logging

import aiohttp

from db import manager
from events.stat_fetcher import extract_stat, fetch_member_data

_POLL_INTERVAL = 900       # 15 minutes between full sweeps
_STARTUP_DELAY = 45        # let the bot finish connecting before the first poll
_SLEEP_BETWEEN_CALLS = 1.2 # seconds between Hypixel API calls


async def _poll_event(event: dict) -> None:
    tasks = manager.get_bingo_tasks(event['id'])
    if not tasks:
        return

    # Collect UUIDs for all participating guilds
    member_uuids: set[str] = set()
    for guild_key in event['guilds']:
        for uuid in manager.get_guild_uuids(guild_key):
            member_uuids.add(uuid)

    if not member_uuids:
        return

    logging.info(f"[BingoTracker] Polling {len(member_uuids)} members for '{event['slug']}'")

    non_free_tasks = [t for t in tasks if t['task_type'] != 'free']

    async with aiohttp.ClientSession() as session:
        for uuid in member_uuids:
            member_data = await fetch_member_data(session, uuid)
            if member_data is None:
                await asyncio.sleep(_SLEEP_BETWEEN_CALLS)
                continue

            for task in non_free_tasks:
                current_val = extract_stat(member_data, task['task_type'], task['target'])
                target_amount = float(task['target'].get('amount', 1))

                existing = manager.get_bingo_progress_entry(event['id'], uuid, task['id'])
                if existing is None:
                    # First time we've seen this member — snapshot as baseline
                    manager.upsert_bingo_baseline(event['id'], uuid, task['id'], current_val)
                else:
                    manager.update_bingo_progress(event['id'], uuid, task['id'], current_val, target_amount)

            await asyncio.sleep(_SLEEP_BETWEEN_CALLS)

    logging.info(f"[BingoTracker] Done polling '{event['slug']}'")


async def run() -> None:
    """Entry point — runs forever as an asyncio task alongside the Discord bot."""
    await asyncio.sleep(_STARTUP_DELAY)
    while True:
        try:
            active_events = manager.get_events(include_drafts=False)
            for event in active_events:
                if event['type'] == 'bingo':
                    await _poll_event(event)
        except Exception:
            logging.exception("[BingoTracker] Unhandled error during poll cycle")
        await asyncio.sleep(_POLL_INTERVAL)
