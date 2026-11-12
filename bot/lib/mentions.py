"""Turns `@name` in Minecraft guild chat into safe Discord pings.

The text is never passed to Discord as-is. Each `@name` is looked up here and either becomes a
real `<@id>` mention (at most MAX_PINGS per message) or is defused so it cannot notify anyone.
`@everyone`, `@here`, role mentions and raw `<@123>` typed in game are always defused. The
caller must also send with `allowed_mentions_for(ids)` so Discord itself refuses anything else.
"""
import re

import discord

from db import manager

MAX_PINGS = 3
_MAX_LOOKUPS = 10
_ZWSP = "​"
_TOKEN = re.compile(r"@([A-Za-z0-9_.]{2,32})")
_RAW_MENTION = re.compile(r"<(@|#)")


def allowed_mentions_for(user_ids) -> discord.AllowedMentions:
    """Only these users can be notified; everyone, here and every role never can."""
    return discord.AllowedMentions(
        everyone=False,
        roles=False,
        replied_user=False,
        users=[discord.Object(id=i) for i in user_ids],
    )


def _resolve_name(client, name: str):
    """Returns one Discord id, or None when the name matches nobody or is ambiguous.

    Order: Minecraft name of a linked member, then a linked member's Discord name, then any
    human in the Discord server by username or display name. The first step that finds anyone
    decides; if it finds several people the name is ambiguous and nobody is pinged.
    """
    ign_ids, name_ids = manager.find_discord_ids_by_name(name)
    if ign_ids:
        return ign_ids[0] if len(ign_ids) == 1 else None
    if name_ids:
        return name_ids[0] if len(name_ids) == 1 else None
    lowered = name.lower()
    found = {
        m.id
        for m in client.get_all_members()
        if not m.bot and lowered in (m.name.lower(), m.display_name.lower())
    }
    return found.pop() if len(found) == 1 else None


def resolve_mentions(client, text: str) -> tuple[str, list[int]]:
    """Returns (discord_safe_text, user_ids_to_ping). Blocking (DB): run it off the event loop."""
    ids: list[int] = []
    cache: dict[str, int | None] = {}
    lookups = 0

    def replace(m: re.Match) -> str:
        nonlocal lookups
        name = m.group(1).rstrip(".")
        key = name.lower()
        if key in ("everyone", "here"):
            return f"@{_ZWSP}{m.group(1)}"
        if key not in cache:
            if lookups >= _MAX_LOOKUPS:
                cache[key] = None
            else:
                lookups += 1
                try:
                    cache[key] = _resolve_name(client, name)
                except Exception:
                    cache[key] = None
        user_id = cache[key]
        if user_id is None:
            return f"@{_ZWSP}{m.group(1)}"
        if user_id not in ids:
            if len(ids) >= MAX_PINGS:
                return f"@{_ZWSP}{m.group(1)}"
            ids.append(user_id)
        trailing = m.group(1)[len(name):]
        return f"<@{user_id}>{trailing}"

    # Defuse hand-typed mention syntax first so it can't survive next to a real mention.
    text = _RAW_MENTION.sub(lambda m: f"<{_ZWSP}{m.group(1)}", text)
    return _TOKEN.sub(replace, text), ids
