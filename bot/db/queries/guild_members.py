import time as _time
from typing import Optional

from psycopg2.extras import execute_values

from db.base import BaseQueries


class GuildMembersQueries(BaseQueries):
    """Guild roster, per-member stats, and auto-refresh scheduling (`guild_members`)."""

    def get_guild_members(self, guild_key: str) -> list:
        with self._cursor() as cur:
            cur.execute(
                "SELECT gm.ign, gm.rank, gm.skyblock_level, gm.last_login, gm.uuid, "
                "u.discord_name, u.discord_id, u.discord_avatar, gm.stats_fetched_at "
                "FROM guild_members gm "
                "LEFT JOIN users u ON u.uuid = gm.uuid "
                "WHERE gm.guild_key = %s ORDER BY LOWER(gm.ign)",
                (guild_key,),
            )
            return cur.fetchall()

    def get_member_uuid(self, guild_key: str, ign: str) -> Optional[str]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT uuid FROM guild_members WHERE guild_key = %s AND LOWER(ign) = LOWER(%s)",
                (guild_key, ign),
            )
            row = cur.fetchone()
            return row[0] if row and row[0] else None

    def get_guild_key_for_ign(self, ign: str) -> Optional[str]:
        """Returns the guild_key the IGN currently belongs to, or None."""
        with self._cursor() as cur:
            cur.execute(
                "SELECT guild_key FROM guild_members WHERE LOWER(ign) = LOWER(%s) LIMIT 1",
                (ign,),
            )
            row = cur.fetchone()
            return row[0] if row else None

    def get_guild_members_with_uuid(self, guild_key: str) -> list:
        with self._cursor() as cur:
            cur.execute(
                "SELECT ign, uuid FROM guild_members WHERE guild_key = %s",
                (guild_key,),
            )
            return cur.fetchall()

    def upsert_guild_member(self, guild_key: str, ign: str, rank: str = '') -> None:
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO guild_members (guild_key, ign, rank) VALUES (%s, %s, %s) "
                "ON CONFLICT (guild_key, ign) DO UPDATE SET rank = EXCLUDED.rank",
                (guild_key, ign, rank),
            )

    def remove_guild_member(self, guild_key: str, ign: str) -> None:
        with self._cursor() as cur:
            cur.execute(
                "DELETE FROM guild_members WHERE guild_key = %s AND LOWER(ign) = LOWER(%s)",
                (guild_key, ign),
            )

    def sync_guild_members(self, guild_key: str, members: list) -> None:
        with self._cursor() as cur:
            # Fetch existing IGNs for this guild
            cur.execute(
                "SELECT ign FROM guild_members WHERE guild_key = %s", (guild_key,)
            )
            existing = {row[0].lower() for row in cur.fetchall()}
            new_igns = {m['ign'].lower() for m in members}

            # Remove members no longer in guild (case-insensitive)
            for ign_lower in existing - new_igns:
                cur.execute(
                    "DELETE FROM guild_members WHERE guild_key = %s AND LOWER(ign) = %s",
                    (guild_key, ign_lower),
                )

            # Batch upsert, preserving stats columns
            if members:
                execute_values(
                    cur,
                    "INSERT INTO guild_members (guild_key, ign, uuid, rank) VALUES %s "
                    "ON CONFLICT (guild_key, ign) DO UPDATE SET "
                    "uuid = COALESCE(EXCLUDED.uuid, guild_members.uuid), "
                    "rank = EXCLUDED.rank",
                    [(guild_key, m['ign'], m.get('uuid') or None, m.get('rank', '')) for m in members],
                )

    def update_guild_member_stats(self, guild_key: str, ign: str, skyblock_level, last_login) -> None:
        with self._cursor() as cur:
            cur.execute(
                "UPDATE guild_members SET skyblock_level = %s, last_login = %s, stats_fetched_at = %s "
                "WHERE guild_key = %s AND LOWER(ign) = LOWER(%s)",
                (skyblock_level, last_login, int(_time.time()), guild_key, ign),
            )

    def update_guild_member_uuid(self, guild_key: str, ign: str, uuid: str) -> None:
        with self._cursor() as cur:
            cur.execute(
                "UPDATE guild_members SET uuid = %s WHERE guild_key = %s AND LOWER(ign) = LOWER(%s)",
                (uuid, guild_key, ign),
            )

    def get_oldest_stats_member(self) -> Optional[tuple]:
        """Returns (guild_key, ign, uuid, rank) for the member with oldest or missing stats."""
        with self._cursor() as cur:
            cur.execute(
                "SELECT guild_key, ign::TEXT, uuid, rank FROM guild_members "
                "ORDER BY stats_fetched_at ASC NULLS FIRST LIMIT 1"
            )
            return cur.fetchone()
