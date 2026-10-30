"""Keeps a linked member's Discord rank role in step with their guild rank.

A rank's Discord role is the one named exactly like the Hypixel rank ("Sweaty Bee"), unless the
guild's Config page picks a different role for it (`guild_config.rank_roles`).
`sync_member_roles` gives a linked member the role for their current rank and takes away every
other rank role, so a demotion swaps the role and a move between the guilds does too.
Only rank roles are ever touched; a rank with no matching role is left alone."""
import logging

import discord

from db import manager
from lib.guild_settings import get_rank_roles


def resolve_rank_roles(client, config) -> dict:
    """{bot_rank: role_id}: the role picked on the Config page, else a role named like the rank."""
    roles = get_rank_roles(config)
    by_name = {}
    for server in client.guilds:
        for role in server.roles:
            if not role.is_default() and not role.managed:
                by_name.setdefault(role.name.lower(), role.id)
    for hypixel_rank, bot_rank in config.discord_rank_map.items():
        if bot_rank not in roles and hypixel_rank.lower() in by_name:
            roles[bot_rank] = by_name[hypixel_rank.lower()]
    return roles


def _managed_role_ids(client) -> set:
    return {rid for config in client.guild_configs.values() for rid in resolve_rank_roles(client, config).values()}


async def sync_member_roles(client, uuid) -> None:
    """Adds the member's rank role and removes the other mapped ones, on every Discord server the bot
    shares with them. Never raises: a missing permission or an unknown member is only logged."""
    if not uuid:
        return
    try:
        user = manager.get_user_by_uuid(uuid)
        member_row = manager.get_member_by_uuid(uuid)
        if not user or not user[1] or not member_row:
            return  # not linked to Discord, or not in a guild: nothing to sync
        discord_id = int(user[1])
        guild_key, hypixel_rank = member_row
        config = client.guild_configs.get(guild_key)
        if config is None:
            return
        bot_rank = config.discord_rank_map.get(hypixel_rank)
        if bot_rank is None:
            return  # rank not known yet (fresh join, partial name); the next refresh retries
        wanted = resolve_rank_roles(client, config).get(bot_rank)
        managed = _managed_role_ids(client)
        if not managed:
            return

        for server in client.guilds:
            member = server.get_member(discord_id)
            if member is None:
                continue
            held = {r.id for r in member.roles}
            to_remove = [server.get_role(rid) for rid in managed if rid in held and rid != wanted]
            to_add = server.get_role(wanted) if wanted and wanted not in held else None
            try:
                if to_remove:
                    await member.remove_roles(*[r for r in to_remove if r], reason="Guild rank sync")
                if to_add:
                    await member.add_roles(to_add, reason="Guild rank sync")
            except discord.Forbidden:
                logging.warning(f"[roles] Missing permission to change roles for {user[0]} in {server.name} "
                                f"(the bot's role must be above the rank roles and have Manage Roles)")
            except discord.HTTPException as e:
                logging.warning(f"[roles] Could not change roles for {user[0]}: {e}")
    except Exception as e:
        logging.warning(f"[roles] Sync failed for {uuid}: {e}")
