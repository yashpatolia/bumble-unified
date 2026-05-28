#!/usr/bin/env python3
"""
One-time import of message history from a Discord channel into message_counts.

Usage (run from bot/ directory):
    set -a && source .env && set +a
    python ../scripts/import_message_history.py --channel CHANNEL_ID --guild bk
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "bot"))

import aiohttp


async def fetch_all_messages(token: str, channel_id: str) -> dict:
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


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", required=True, help="Discord channel ID")
    parser.add_argument("--guild", required=True, choices=["bk", "bu"], help="Guild key")
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
    print("Writing to database (only guild members will be included)...")
    manager.bulk_increment_message_counts(args.guild, counts)
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
