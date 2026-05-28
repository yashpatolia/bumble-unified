import time as _time
from contextlib import contextmanager
from typing import Optional

import psycopg2
import psycopg2.pool
from psycopg2.extras import execute_values


class DatabaseManager:
    """Centralized PostgreSQL access via a threaded connection pool."""

    def __init__(self, dsn: str):
        self._pool = psycopg2.pool.ThreadedConnectionPool(minconn=1, maxconn=10, dsn=dsn)

    @contextmanager
    def _cursor(self):
        conn = self._pool.getconn()
        try:
            with conn.cursor() as cur:
                yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self._pool.putconn(conn)

    # --- Users ---

    def get_user_by_discord(self, discord_id: int) -> Optional[tuple]:
        """Returns (ign, discord_name, uuid) or None."""
        with self._cursor() as cur:
            cur.execute(
                "SELECT ign, discord_name, uuid FROM users WHERE discord_id = %s",
                (discord_id,),
            )
            return cur.fetchone()

    def get_user_by_ign(self, ign: str) -> Optional[tuple]:
        """Returns (ign, discord_name, uuid) or None."""
        with self._cursor() as cur:
            cur.execute(
                "SELECT ign, discord_name, uuid FROM users WHERE LOWER(ign) = LOWER(%s)",
                (ign,),
            )
            return cur.fetchone()

    def get_ign(self, discord_id: int) -> Optional[str]:
        with self._cursor() as cur:
            cur.execute("SELECT ign FROM users WHERE discord_id = %s", (discord_id,))
            row = cur.fetchone()
            return row[0] if row else None

    def get_uuid_by_discord(self, discord_id: int) -> Optional[str]:
        with self._cursor() as cur:
            cur.execute("SELECT uuid FROM users WHERE discord_id = %s", (discord_id,))
            row = cur.fetchone()
            return row[0] if row else None

    def get_discord_id_by_uuid(self, uuid: str) -> Optional[int]:
        with self._cursor() as cur:
            cur.execute("SELECT discord_id FROM users WHERE uuid = %s", (uuid,))
            row = cur.fetchone()
            return row[0] if row else None

    def is_linked(self, uuid: str) -> bool:
        with self._cursor() as cur:
            cur.execute("SELECT discord_id FROM users WHERE uuid = %s", (uuid,))
            row = cur.fetchone()
            return row is not None and row[0] is not None

    def link_user(self, uuid: str, ign: str, discord_id: int, discord_name: str) -> None:
        """Insert a new user or update an existing record with Discord info."""
        with self._cursor() as cur:
            cur.execute("SELECT uuid FROM users WHERE uuid = %s", (uuid,))
            existing = cur.fetchone()
            if existing:
                cur.execute(
                    "UPDATE users SET discord_id = %s, discord_name = %s WHERE uuid = %s",
                    (discord_id, discord_name, uuid),
                )
            else:
                cur.execute(
                    "INSERT INTO users (uuid, ign, discord_id, discord_name) VALUES (%s, %s, %s, %s)",
                    (uuid, ign, discord_id, discord_name),
                )

    # --- Dyes ---

    def get_dye_info(self, dye_id: str) -> Optional[tuple]:
        """Returns (hex, dye_name) or None."""
        with self._cursor() as cur:
            cur.execute("SELECT hex, dye_name FROM dyes WHERE dye_id = %s", (dye_id,))
            return cur.fetchone()

    def get_unlocked_dyes(self, uuid: str) -> list[str]:
        """Returns list of dye_id strings the user has received."""
        with self._cursor() as cur:
            cur.execute(
                "SELECT dye_id FROM users_dyes WHERE uuid = %s AND received = TRUE",
                (uuid,),
            )
            return [row[0] for row in cur.fetchall()]

    def get_all_dyes_weighted(self) -> list[tuple]:
        """Returns [(dye_id, weight), ...] for all dyes."""
        with self._cursor() as cur:
            cur.execute("SELECT dye_id, weight FROM dyes")
            return cur.fetchall()

    def get_dye_received(self, uuid: str, dye_id: str) -> bool:
        with self._cursor() as cur:
            cur.execute(
                "SELECT received FROM users_dyes WHERE dye_id = %s AND uuid = %s",
                (dye_id, uuid),
            )
            row = cur.fetchone()
            return bool(row[0]) if row else False

    def get_dye_details(self, dye_id: str) -> Optional[tuple]:
        """Returns (dye_name, weight, hex) or None."""
        with self._cursor() as cur:
            cur.execute(
                "SELECT dye_name, weight, hex FROM dyes WHERE dye_id = %s", (dye_id,)
            )
            return cur.fetchone()

    def mark_dye_received(self, uuid: str, dye_id: str) -> None:
        with self._cursor() as cur:
            cur.execute(
                "UPDATE users_dyes SET received = TRUE WHERE dye_id = %s AND uuid = %s",
                (dye_id, uuid),
            )

    def add_dye(self, dye_id: str, dye_name: str, weight: float, hex_color: str) -> None:
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO dyes (dye_id, dye_name, weight, hex) VALUES (%s, %s, %s, %s) "
                "ON CONFLICT DO NOTHING",
                (dye_id, dye_name.title(), weight, hex_color.capitalize()),
            )

    def remove_dye(self, dye_id: str) -> None:
        with self._cursor() as cur:
            cur.execute("DELETE FROM dyes WHERE dye_id = %s", (dye_id,))

    # --- Guild Members ---

    def get_guild_members(self, guild_key: str) -> list:
        with self._cursor() as cur:
            cur.execute(
                "SELECT gm.ign, gm.rank, gm.skyblock_level, gm.last_login, gm.uuid, "
                "u.discord_name, u.discord_id "
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

    # --- Panel Users ---

    def get_panel_user(self, discord_id: int) -> Optional[tuple]:
        """Returns (discord_id, discord_name, is_admin, can_view_logs, can_control_bots, can_fetch_api, can_manage_links) or None."""
        with self._cursor() as cur:
            cur.execute(
                "SELECT discord_id, discord_name, is_admin, can_view_logs, can_control_bots, can_fetch_api, can_manage_links "
                "FROM panel_users WHERE discord_id = %s",
                (discord_id,),
            )
            return cur.fetchone()

    def get_all_panel_users(self) -> list:
        with self._cursor() as cur:
            cur.execute(
                "SELECT discord_id, discord_name, is_admin, can_view_logs, can_control_bots, can_fetch_api, can_manage_links "
                "FROM panel_users"
            )
            return cur.fetchall()

    def create_panel_user(
        self,
        discord_id: int,
        discord_name: str,
        is_admin: bool = False,
        can_view_logs: bool = True,
        can_control_bots: bool = False,
        can_fetch_api: bool = False,
        can_manage_links: bool = False,
    ) -> None:
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO panel_users (discord_id, discord_name, is_admin, can_view_logs, can_control_bots, can_fetch_api, can_manage_links) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                (discord_id, discord_name, is_admin, can_view_logs, can_control_bots, can_fetch_api, can_manage_links),
            )

    def upsert_panel_user_name(self, discord_id: int, discord_name: str) -> None:
        with self._cursor() as cur:
            cur.execute(
                "UPDATE panel_users SET discord_name = %s WHERE discord_id = %s",
                (discord_name, discord_id),
            )

    def update_panel_user_permissions(
        self,
        discord_id: int,
        is_admin: bool,
        can_view_logs: bool,
        can_control_bots: bool,
        can_fetch_api: bool = False,
        can_manage_links: bool = False,
    ) -> None:
        with self._cursor() as cur:
            cur.execute(
                "UPDATE panel_users SET is_admin = %s, can_view_logs = %s, can_control_bots = %s, "
                "can_fetch_api = %s, can_manage_links = %s WHERE discord_id = %s",
                (is_admin, can_view_logs, can_control_bots, can_fetch_api, can_manage_links, discord_id),
            )

    def unlink_user(self, uuid: str) -> None:
        with self._cursor() as cur:
            cur.execute(
                "UPDATE users SET discord_id = NULL, discord_name = NULL WHERE uuid = %s",
                (uuid,),
            )

    def delete_panel_user(self, discord_id: int) -> None:
        with self._cursor() as cur:
            cur.execute("DELETE FROM panel_users WHERE discord_id = %s", (discord_id,))

    # --- Message Counts ---

    def increment_message_count(self, guild_key: str, ign: str) -> None:
        """Increment lifetime, current month, and current week counts for an IGN."""
        import datetime
        now = datetime.datetime.utcnow()
        month_key = now.strftime('%Y-%m')
        week_key = now.strftime('%G-W%V')  # ISO week
        periods = [('lifetime', ''), ('month', month_key), ('week', week_key)]
        with self._cursor() as cur:
            for period_type, period_key in periods:
                cur.execute(
                    "INSERT INTO message_counts (guild_key, ign, period_type, period_key, count) "
                    "VALUES (%s, %s, %s, %s, 1) "
                    "ON CONFLICT (guild_key, ign, period_type, period_key) "
                    "DO UPDATE SET count = message_counts.count + 1",
                    (guild_key, ign, period_type, period_key)
                )

    def get_message_leaderboard(self, guild_key: str, period_type: str, period_key: str) -> list:
        """Returns [(ign, count, uuid, discord_name, discord_id), ...] sorted by count desc."""
        with self._cursor() as cur:
            cur.execute(
                "SELECT mc.ign, mc.count, gm.uuid, u.discord_name, u.discord_id "
                "FROM message_counts mc "
                "LEFT JOIN guild_members gm ON gm.guild_key = mc.guild_key AND LOWER(gm.ign) = LOWER(mc.ign) "
                "LEFT JOIN users u ON u.uuid = gm.uuid "
                "WHERE mc.guild_key = %s AND mc.period_type = %s AND mc.period_key = %s "
                "ORDER BY mc.count DESC",
                (guild_key, period_type, period_key)
            )
            return cur.fetchall()

    def bulk_increment_message_counts(self, guild_key: str, counts: dict) -> None:
        """counts is {ign: count}. Used for bulk import. Only increments for IGNs in guild_members."""
        with self._cursor() as cur:
            for ign, count in counts.items():
                # Verify IGN is in guild_members (case-insensitive via citext)
                cur.execute(
                    "SELECT ign FROM guild_members WHERE guild_key = %s AND ign = %s",
                    (guild_key, ign)
                )
                row = cur.fetchone()
                if not row:
                    continue
                actual_ign = row[0]  # Use the properly-cased IGN from DB
                cur.execute(
                    "INSERT INTO message_counts (guild_key, ign, period_type, period_key, count) "
                    "VALUES (%s, %s, 'lifetime', '', %s) "
                    "ON CONFLICT (guild_key, ign, period_type, period_key) "
                    "DO UPDATE SET count = message_counts.count + %s",
                    (guild_key, actual_ign, count, count)
                )
