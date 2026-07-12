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

    def get_user_by_uuid(self, uuid: str) -> Optional[tuple]:
        """Returns (ign, discord_id, discord_name, discord_avatar) or None."""
        with self._cursor() as cur:
            cur.execute(
                "SELECT ign, discord_id, discord_name, discord_avatar FROM users WHERE uuid = %s",
                (uuid,),
            )
            return cur.fetchone()

    def search_users_with_dye_counts(self, query: str, limit: int = 20) -> list[tuple]:
        """Returns [(uuid, ign, discord_id, discord_name, discord_avatar, unlocked_count), ...]
        for users whose IGN matches query, ordered by IGN."""
        with self._cursor() as cur:
            cur.execute(
                "SELECT u.uuid, u.ign, u.discord_id, u.discord_name, u.discord_avatar, "
                "COUNT(ud.dye_id) FILTER (WHERE ud.received) AS unlocked_count "
                "FROM users u "
                "LEFT JOIN users_dyes ud ON ud.uuid = u.uuid "
                "WHERE u.ign ILIKE %s "
                "GROUP BY u.uuid "
                "ORDER BY u.ign "
                "LIMIT %s",
                (f"%{query}%", limit),
            )
            return cur.fetchall()

    def is_linked(self, uuid: str) -> bool:
        with self._cursor() as cur:
            cur.execute("SELECT discord_id FROM users WHERE uuid = %s", (uuid,))
            row = cur.fetchone()
            return row is not None and row[0] is not None

    def link_user(self, uuid: str, ign: str, discord_id: int, discord_name: str, discord_avatar: str = None) -> None:
        """Insert a new user or update an existing record with Discord info."""
        with self._cursor() as cur:
            # Clear any previous link for this discord_id so one Discord account maps to exactly one UUID
            cur.execute(
                "UPDATE users SET discord_id = NULL, discord_name = NULL WHERE discord_id = %s AND uuid != %s",
                (discord_id, uuid),
            )
            cur.execute("SELECT uuid FROM users WHERE uuid = %s", (uuid,))
            existing = cur.fetchone()
            if existing:
                cur.execute(
                    "UPDATE users SET discord_id = %s, discord_name = %s, discord_avatar = COALESCE(%s, discord_avatar) WHERE uuid = %s",
                    (discord_id, discord_name, discord_avatar, uuid),
                )
            else:
                cur.execute(
                    "INSERT INTO users (uuid, ign, discord_id, discord_name, discord_avatar) VALUES (%s, %s, %s, %s, %s)",
                    (uuid, ign, discord_id, discord_name, discord_avatar),
                )

    def update_user_avatar(self, discord_id: int, discord_avatar: str) -> None:
        with self._cursor() as cur:
            cur.execute(
                "UPDATE users SET discord_avatar = %s WHERE discord_id = %s",
                (discord_avatar, discord_id),
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

    def get_all_dyes(self) -> list[tuple]:
        """Returns [(dye_id, dye_name, weight, hex), ...] for all dyes, commonest first."""
        with self._cursor() as cur:
            cur.execute("SELECT dye_id, dye_name, weight, hex FROM dyes ORDER BY weight DESC")
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
                "INSERT INTO users_dyes (uuid, dye_id, received, unlocked_at) VALUES (%s, %s, TRUE, NOW()) "
                "ON CONFLICT (uuid, dye_id) DO UPDATE SET received = TRUE, unlocked_at = NOW()",
                (uuid, dye_id),
            )

    def get_recent_drops(self, limit: int = 20) -> list[tuple]:
        """Returns [(dye_id, dye_name, hex, unlocked_at, uuid, ign, discord_name, discord_avatar), ...],
        most recent first."""
        with self._cursor() as cur:
            cur.execute(
                "SELECT ud.dye_id, d.dye_name, d.hex, ud.unlocked_at, "
                "u.uuid, u.ign, u.discord_name, u.discord_avatar "
                "FROM users_dyes ud "
                "JOIN dyes d ON d.dye_id = ud.dye_id "
                "JOIN users u ON u.uuid = ud.uuid "
                "WHERE ud.received = TRUE AND ud.unlocked_at IS NOT NULL "
                "ORDER BY ud.unlocked_at DESC "
                "LIMIT %s",
                (limit,),
            )
            return cur.fetchall()

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

    def reset_all_dye_rolls(self) -> int:
        """Delete every player's dye-unlock records. Returns the number of rows removed."""
        with self._cursor() as cur:
            cur.execute("DELETE FROM users_dyes")
            return cur.rowcount

    # --- Guild Members ---

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

    # --- API Usage Tracking ---

    def record_api_call(self, endpoint: str, success: bool = True) -> None:
        import datetime as _dt
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO api_calls (called_at, endpoint, success) VALUES (%s, %s, %s)",
                (_dt.datetime.now(_dt.timezone.utc), endpoint, success),
            )

    def get_api_call_counts(self) -> dict:
        """Returns API call counts for several rolling windows."""
        import datetime as _dt
        now = _dt.datetime.now(_dt.timezone.utc)
        windows = {
            "last_minute": now - _dt.timedelta(minutes=1),
            "last_5min": now - _dt.timedelta(minutes=5),
            "last_hour": now - _dt.timedelta(hours=1),
            "today": now - _dt.timedelta(hours=24),
        }
        result = {}
        with self._cursor() as cur:
            for key, since in windows.items():
                cur.execute("SELECT COUNT(*) FROM api_calls WHERE called_at >= %s", (since,))
                result[key] = cur.fetchone()[0]
        return result

    # --- Panel Users ---

    def get_panel_user(self, discord_id: int) -> Optional[tuple]:
        """Returns (discord_id, discord_name, is_admin, can_control_bots, can_fetch_api, can_manage_links) or None."""
        with self._cursor() as cur:
            cur.execute(
                "SELECT discord_id, discord_name, is_admin, can_control_bots, can_fetch_api, can_manage_links "
                "FROM panel_users WHERE discord_id = %s",
                (discord_id,),
            )
            return cur.fetchone()

    def get_all_panel_users(self) -> list:
        with self._cursor() as cur:
            cur.execute(
                "SELECT discord_id, discord_name, is_admin, can_control_bots, can_fetch_api, can_manage_links "
                "FROM panel_users"
            )
            return cur.fetchall()

    def create_panel_user(
        self,
        discord_id: int,
        discord_name: str,
        is_admin: bool = False,
        can_control_bots: bool = False,
        can_fetch_api: bool = False,
        can_manage_links: bool = False,
    ) -> None:
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO panel_users (discord_id, discord_name, is_admin, can_control_bots, can_fetch_api, can_manage_links) "
                "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                (discord_id, discord_name, is_admin, can_control_bots, can_fetch_api, can_manage_links),
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
        can_control_bots: bool,
        can_fetch_api: bool = False,
        can_manage_links: bool = False,
    ) -> None:
        with self._cursor() as cur:
            cur.execute(
                "UPDATE panel_users SET is_admin = %s, can_control_bots = %s, "
                "can_fetch_api = %s, can_manage_links = %s WHERE discord_id = %s",
                (is_admin, can_control_bots, can_fetch_api, can_manage_links, discord_id),
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
        """Increment lifetime, current month, and current week counts for a player."""
        import datetime
        now = datetime.datetime.utcnow()
        month_key = now.strftime('%Y-%m')
        week_key = now.strftime('%G-W%V')  # ISO week
        periods = [('lifetime', ''), ('month', month_key), ('week', week_key)]
        with self._cursor() as cur:
            # Resolve UUID and canonical IGN from guild_members (citext match is case-insensitive)
            cur.execute(
                "SELECT uuid, ign::TEXT FROM guild_members WHERE guild_key = %s AND ign = %s",
                (guild_key, ign)
            )
            row = cur.fetchone()
            if not row or not row[0]:
                return
            uuid, canonical_ign = row
            for period_type, period_key in periods:
                cur.execute(
                    "INSERT INTO message_counts (guild_key, uuid, ign, period_type, period_key, count) "
                    "VALUES (%s, %s, %s, %s, %s, 1) "
                    "ON CONFLICT (guild_key, uuid, period_type, period_key) WHERE uuid IS NOT NULL AND uuid != '' "
                    "DO UPDATE SET count = message_counts.count + 1, ign = EXCLUDED.ign",
                    (guild_key, uuid, canonical_ign, period_type, period_key)
                )

    def get_message_leaderboard(self, guild_key: str, period_type: str, period_key: str) -> list:
        """Returns [(ign, count, uuid, discord_name, discord_id, discord_avatar), ...] sorted by count desc."""
        with self._cursor() as cur:
            cur.execute(
                "SELECT mc.ign, mc.count, mc.uuid, u.discord_name, u.discord_id, u.discord_avatar "
                "FROM message_counts mc "
                "LEFT JOIN users u ON u.uuid = mc.uuid "
                "WHERE mc.guild_key = %s AND mc.period_type = %s AND mc.period_key = %s "
                "  AND mc.uuid IS NOT NULL AND mc.uuid != '' "
                "ORDER BY mc.count DESC",
                (guild_key, period_type, period_key)
            )
            return cur.fetchall()

    def bulk_increment_message_counts(self, guild_key: str, counts: dict) -> None:
        """counts is {ign: count}. Used for bulk import. Only increments for IGNs in guild_members."""
        with self._cursor() as cur:
            for ign, count in counts.items():
                cur.execute(
                    "SELECT uuid, ign::TEXT FROM guild_members WHERE guild_key = %s AND ign = %s",
                    (guild_key, ign)
                )
                row = cur.fetchone()
                if not row or not row[0]:
                    continue
                uuid, canonical_ign = row
                cur.execute(
                    "INSERT INTO message_counts (guild_key, uuid, ign, period_type, period_key, count) "
                    "VALUES (%s, %s, %s, 'lifetime', '', %s) "
                    "ON CONFLICT (guild_key, uuid, period_type, period_key) WHERE uuid IS NOT NULL AND uuid != '' "
                    "DO UPDATE SET count = message_counts.count + %s, ign = EXCLUDED.ign",
                    (guild_key, uuid, canonical_ign, count, count)
                )

