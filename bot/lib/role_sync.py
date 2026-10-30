"""Keeps a linked member's Discord roles in step with their guild membership and rank.

Two kinds of role are handed out, both found the same way: the role the guild's Config page picks
(`guild_config.rank_roles` / `member_role`), else the one named exactly like the Hypixel rank
("Sweaty Bee") or the guild ("Bumble University").
- the rank role for their current rank, swapped on a promotion or demotion;
- the guild role for the guild they are in, kept alongside the rank role.
`sync_member_roles` adds what is missing and removes every other rank or guild role, so a demotion
swaps the rank role and a move between the guilds swaps both. Only those roles are ever touched,
and one with no matching Discord role is left alone."""
import logging

import discord

from db import manager
from lib.guild_settings import get_member_role, get_rank_roles


def _roles_by_name(client) -> dict:
    by_name = {}
    for server in client.guilds:
        for role in server.roles:
            if not role.is_default() and not role.managed:
                by_name.setdefault(role.name.lower(), role.id)
    return by_name


def resolve_rank_roles(client, config) -> dict:
    """{bot_rank: role_id}: the role picked on the Config page, else a role named like the rank."""
    roles = get_rank_roles(config)
    by_name = _roles_by_name(client)
    for hypixel_rank, bot_rank in config.discord_rank_map.items():
        if bot_rank not in roles and hypixel_rank.lower() in by_name:
            roles[bot_rank] = by_name[hypixel_rank.lower()]
    return roles


def resolve_guild_role(client, config):
    """The "is in this guild" role: the one picked on the Config page, else a role named like the guild."""
    picked = get_member_role(config)
    if picked:
        return picked
    by_name = _roles_by_name(client)
    for name in (config.display_name, config.guild_name):
        if name and name.lower() in by_name:
            return by_name[name.lower()]
    return None


def _managed_role_ids(client) -> set:
    ids = set()
    for config in client.guild_configs.values():
        ids.update(resolve_rank_roles(client, config).values())
        guild_role = resolve_guild_role(client, config)
        if guild_role:
            ids.add(guild_role)
    return ids


async def sync_member_roles(client, uuid) -> None:
    """Gives the member their rank role and guild role and removes the other managed ones, on every
    Discord server the bot shares with them. Never raises: a missing permission or an unknown member
    is only logged."""
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
        wanted = set()
        guild_role = resolve_guild_role(client, config)
        if guild_role:
            wanted.add(guild_role)
        bot_rank = config.discord_rank_map.get(hypixel_rank)
        if bot_rank is not None:  # unknown while a rank is fresh or partial; the next refresh retries
            rank_role = resolve_rank_roles(client, config).get(bot_rank)
            if rank_role:
                wanted.add(rank_role)
        managed = _managed_role_ids(client)
        if not managed:
            return

        for server in client.guilds:
            member = server.get_member(discord_id)
            if member is None:
                continue
            held = {r.id for r in member.roles}
            to_remove = [server.get_role(rid) for rid in managed if rid in held and rid not in wanted]
            if bot_rank is None:
                # Rank unknown: leave rank roles alone, only fix the guild role.
                rank_ids = {rid for c in client.guild_configs.values() for rid in resolve_rank_roles(client, c).values()}
                to_remove = [r for r in to_remove if r and r.id not in rank_ids]
            to_add = [server.get_role(rid) for rid in wanted if rid not in held]
            try:
                if to_remove:
                    await member.remove_roles(*[r for r in to_remove if r], reason="Guild role sync")
                if to_add:
                    await member.add_roles(*[r for r in to_add if r], reason="Guild role sync")
            except discord.Forbidden:
                logging.warning(f"[roles] Missing permission to change roles for {user[0]} in {server.name} "
                                f"(the bot's role must be above these roles and have Manage Roles)")
            except discord.HTTPException as e:
                logging.warning(f"[roles] Could not change roles for {user[0]}: {e}")
    except Exception as e:
        logging.warning(f"[roles] Sync failed for {uuid}: {e}")
