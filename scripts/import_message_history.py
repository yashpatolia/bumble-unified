#!/usr/bin/env python3
"""
One-time import of message history from a Discord channel into message_counts.

Each IGN is attributed to whichever guild (bk/bu) they are currently a member of.
Messages from players not in any guild are skipped.

Usage (run from bot/ directory):
    set -a && source .env && set +a
    python ../scripts/import_message_history.py --channel CHANNEL_ID
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "bot"))

import aiohttp


async def fetch_all_messages(token: str, channel_id: str) -> dict:
    """Returns {ign_lower: count} for all messages in the channel."""
    counts = {}
    headers = {"Authorization": f"Bot {token}"}
    before = None
    total = 0

    async with aiohttp.ClientSession() as session:
        while True:
            params = {"limit": "100"}
            if before:
                params["before"] = before

            async with session.get(
                f"https://discord.com/api/v10/channels/{channel_id}/messages",
                headers=headers,
                params=params,
            ) as resp:
                if resp.status == 429:
                    retry_after = float((await resp.json()).get("retry_after", 1))
                    await asyncio.sleep(retry_after)
                    continue
                if resp.status != 200:
                    print(f"Error {resp.status}: {await resp.text()}")
                    break
                messages = await resp.json()

            if not messages:
                break

            for msg in messages:
                content = msg.get("content", "")
                if " | " in content:
                    ign = content.split(" | ")[0].strip().lower()
                    if ign:
                        counts[ign] = counts.get(ign, 0) + 1

            total += len(messages)
            if total % 5000 < 100:
                print(f"  Fetched {total} messages so far...")

            before = messages[-1]["id"]
            await asyncio.sleep(0.5)

    print(f"  Total messages fetched: {total}")
    return counts


def build_guild_member_sets(manager) -> dict[str, set]:
    """Returns {guild_key: {ign_lower, ...}} for all guilds."""
    guild_sets = {}
    with manager._cursor() as cur:
        cur.execute("SELECT DISTINCT guild_key FROM guild_members")
        keys = [row[0] for row in cur.fetchall()]
    for key in keys:
        with manager._cursor() as cur:
            cur.execute(
                "SELECT LOWER(ign) FROM guild_members WHERE guild_key = %s", (key,)
            )
            guild_sets[key] = {row[0] for row in cur.fetchall()}
    return guild_sets


def split_counts_by_guild(counts: dict, guild_sets: dict[str, set]) -> dict[str, dict]:
    """
    Split {ign_lower: count} into per-guild dicts.
    Each IGN is credited to the first guild it appears in (bk checked before bu).
    IGNs not in any guild are skipped.
    """
    per_guild = {key: {} for key in guild_sets}
    skipped = 0
    for ign_lower, count in counts.items():
        attributed = False
        for key in ("bk", "bu"):
            if key in guild_sets and ign_lower in guild_sets[key]:
                per_guild[key][ign_lower] = count
                attributed = True
                break
        if not attributed:
            # try any other guild keys that aren't bk/bu
            for key, members in guild_sets.items():
                if key not in ("bk", "bu") and ign_lower in members:
                    per_guild[key][ign_lower] = count
                    attributed = True
                    break
        if not attributed:
            skipped += 1
    return per_guild, skipped


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", required=True, help="Discord channel ID")
    args = parser.parse_args()

    token = os.environ.get("DISCORD_BOT_TOKEN")
    db_url = os.environ.get("DATABASE_URL")
    if not token or not db_url:
        print("ERROR: DISCORD_BOT_TOKEN and DATABASE_URL must be set")
        sys.exit(1)

    print(f"Fetching messages from channel {args.channel}...")
    counts = await fetch_all_messages(token, args.channel)
    print(f"Found {len(counts)} unique IGNs in message history.")

    from db import manager

    print("Loading guild member lists from database...")
    guild_sets = build_guild_member_sets(manager)
    for key, members in guild_sets.items():
        print(f"  {key}: {len(members)} members")

    per_guild, skipped = split_counts_by_guild(counts, guild_sets)
    print(f"  Skipped {skipped} IGNs not found in any guild.")

    print("Writing to database...")
    for key, guild_counts in per_guild.items():
        if guild_counts:
            print(f"  Importing {len(guild_counts)} IGNs into {key}...")
            manager.bulk_increment_message_counts(key, guild_counts)

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
