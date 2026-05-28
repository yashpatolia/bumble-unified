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
                "u.discord_name, u.discord_id, u.discord_avatar "
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
        """Returns (discord_id, discord_name, is_admin, can_control_bots, can_fetch_api, can_manage_links, can_manage_events) or None."""
        with self._cursor() as cur:
            cur.execute(
                "SELECT discord_id, discord_name, is_admin, can_control_bots, can_fetch_api, can_manage_links, can_manage_events "
                "FROM panel_users WHERE discord_id = %s",
                (discord_id,),
            )
            return cur.fetchone()

    def get_all_panel_users(self) -> list:
        with self._cursor() as cur:
            cur.execute(
                "SELECT discord_id, discord_name, is_admin, can_control_bots, can_fetch_api, can_manage_links, can_manage_events "
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
        can_manage_events: bool = False,
    ) -> None:
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO panel_users (discord_id, discord_name, is_admin, can_control_bots, can_fetch_api, can_manage_links, can_manage_events) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                (discord_id, discord_name, is_admin, can_control_bots, can_fetch_api, can_manage_links, can_manage_events),
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
        can_manage_events: bool = False,
    ) -> None:
        with self._cursor() as cur:
            cur.execute(
                "UPDATE panel_users SET is_admin = %s, can_control_bots = %s, "
                "can_fetch_api = %s, can_manage_links = %s, can_manage_events = %s WHERE discord_id = %s",
                (is_admin, can_control_bots, can_fetch_api, can_manage_links, can_manage_events, discord_id),
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

    # --- Events ---

    _EVENT_COLS = ['id', 'slug', 'type', 'name', 'mode', 'guilds', 'status', 'starts_at', 'ends_at', 'created_at']

    def _event_row(self, row: tuple) -> dict:
        return dict(zip(self._EVENT_COLS, row))

    def get_events(self, include_drafts: bool = False) -> list:
        with self._cursor() as cur:
            if include_drafts:
                cur.execute(
                    "SELECT id, slug, type, name, mode, guilds, status, starts_at, ends_at, created_at "
                    "FROM events ORDER BY created_at DESC"
                )
            else:
                cur.execute(
                    "SELECT id, slug, type, name, mode, guilds, status, starts_at, ends_at, created_at "
                    "FROM events WHERE status = 'active' ORDER BY created_at DESC"
                )
            return [self._event_row(r) for r in cur.fetchall()]

    def get_event_by_slug(self, slug: str) -> Optional[dict]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT id, slug, type, name, mode, guilds, status, starts_at, ends_at, created_at "
                "FROM events WHERE slug = %s",
                (slug,),
            )
            row = cur.fetchone()
            return self._event_row(row) if row else None

    def create_event(self, slug: str, name: str, mode: str, guilds: list, starts_at, ends_at) -> int:
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO events (slug, type, name, mode, guilds, starts_at, ends_at) "
                "VALUES (%s, 'bingo', %s, %s, %s, %s, %s) RETURNING id",
                (slug, name, mode, guilds, starts_at, ends_at),
            )
            event_id = cur.fetchone()[0]
            # Pre-insert free space at centre (position 12)
            cur.execute(
                "INSERT INTO bingo_tasks (event_id, position, name, task_type, target) "
                "VALUES (%s, 12, 'Free Space', 'free', '{}') ON CONFLICT DO NOTHING",
                (event_id,),
            )
            return event_id

    def update_event(self, slug: str, name: str, mode: str, guilds: list, starts_at, ends_at) -> None:
        with self._cursor() as cur:
            cur.execute(
                "UPDATE events SET name = %s, mode = %s, guilds = %s, starts_at = %s, ends_at = %s "
                "WHERE slug = %s",
                (name, mode, guilds, starts_at, ends_at, slug),
            )

    def update_event_status(self, slug: str, status: str) -> None:
        with self._cursor() as cur:
            cur.execute("UPDATE events SET status = %s WHERE slug = %s", (status, slug))

    def delete_event(self, slug: str) -> None:
        with self._cursor() as cur:
            cur.execute("DELETE FROM events WHERE slug = %s", (slug,))

    # --- Bingo tasks ---

    _TASK_COLS = ['id', 'event_id', 'position', 'name', 'description', 'task_type', 'target', 'difficulty']

    def _task_row(self, row: tuple) -> dict:
        return dict(zip(self._TASK_COLS, row))

    def get_bingo_tasks(self, event_id: int) -> list:
        with self._cursor() as cur:
            cur.execute(
                "SELECT id, event_id, position, name, description, task_type, target, difficulty "
                "FROM bingo_tasks WHERE event_id = %s ORDER BY position",
                (event_id,),
            )
            return [self._task_row(r) for r in cur.fetchall()]

    def upsert_bingo_task(self, event_id: int, position: int, name: str, description: str,
                          task_type: str, target: dict, difficulty: str) -> None:
        import json as _json
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO bingo_tasks (event_id, position, name, description, task_type, target, difficulty) "
                "VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s) "
                "ON CONFLICT (event_id, position) DO UPDATE SET "
                "name = EXCLUDED.name, description = EXCLUDED.description, "
                "task_type = EXCLUDED.task_type, target = EXCLUDED.target, difficulty = EXCLUDED.difficulty",
                (event_id, position, name, description, task_type, _json.dumps(target), difficulty),
            )

    def delete_bingo_task(self, event_id: int, position: int) -> None:
        with self._cursor() as cur:
            cur.execute(
                "DELETE FROM bingo_tasks WHERE event_id = %s AND position = %s AND task_type != 'free'",
                (event_id, position),
            )

    # --- Bingo progress ---

    def get_guild_uuids(self, guild_key: str) -> list:
        with self._cursor() as cur:
            cur.execute(
                "SELECT uuid FROM guild_members WHERE guild_key = %s AND uuid IS NOT NULL AND uuid != ''",
                (guild_key,),
            )
            return [r[0] for r in cur.fetchall()]

    def get_bingo_progress_entry(self, event_id: int, uuid: str, task_id: int) -> Optional[dict]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT baseline, current_val, completed FROM bingo_progress "
                "WHERE event_id = %s AND uuid = %s AND task_id = %s",
                (event_id, uuid, task_id),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {'baseline': row[0], 'current_val': row[1], 'completed': row[2]}

    def upsert_bingo_baseline(self, event_id: int, uuid: str, task_id: int, baseline: float) -> None:
        import datetime as _dt
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO bingo_progress (event_id, uuid, task_id, baseline, current_val, last_updated) "
                "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                (event_id, uuid, task_id, baseline, baseline, _dt.datetime.now(_dt.timezone.utc)),
            )

    def update_bingo_progress(self, event_id: int, uuid: str, task_id: int,
                               current_val: float, target_amount: float) -> None:
        import datetime as _dt
        now = _dt.datetime.now(_dt.timezone.utc)
        with self._cursor() as cur:
            cur.execute(
                "SELECT baseline, completed FROM bingo_progress "
                "WHERE event_id = %s AND uuid = %s AND task_id = %s",
                (event_id, uuid, task_id),
            )
            row = cur.fetchone()
            if not row:
                return
            baseline, already_done = row
            newly_done = not already_done and (current_val - baseline) >= target_amount
            if newly_done:
                cur.execute(
                    "UPDATE bingo_progress SET current_val = %s, completed = TRUE, "
                    "completed_at = %s, last_updated = %s "
                    "WHERE event_id = %s AND uuid = %s AND task_id = %s",
                    (current_val, now, now, event_id, uuid, task_id),
                )
            else:
                cur.execute(
                    "UPDATE bingo_progress SET current_val = %s, last_updated = %s "
                    "WHERE event_id = %s AND uuid = %s AND task_id = %s",
                    (current_val, now, event_id, uuid, task_id),
                )

    def get_player_bingo_card(self, event_id: int, uuid: str) -> list:
        """Returns all 25 squares with progress data for a specific player."""
        with self._cursor() as cur:
            cur.execute(
                "SELECT bt.id, bt.position, bt.name, bt.description, bt.task_type, bt.target, bt.difficulty, "
                "bp.baseline, bp.current_val, bp.completed, bp.completed_at, bp.last_updated "
                "FROM bingo_tasks bt "
                "LEFT JOIN bingo_progress bp ON bp.task_id = bt.id AND bp.uuid = %s AND bp.event_id = %s "
                "WHERE bt.event_id = %s ORDER BY bt.position",
                (uuid, event_id, event_id),
            )
            cols = ['id', 'position', 'name', 'description', 'task_type', 'target', 'difficulty',
                    'baseline', 'current_val', 'completed', 'completed_at', 'last_updated']
            return [dict(zip(cols, r)) for r in cur.fetchall()]

    def get_bingo_leaderboard(self, event_id: int) -> list:
        """Returns players ranked by completed squares (blackout = all 24 non-free squares done)."""
        with self._cursor() as cur:
            cur.execute(
                "SELECT bp.uuid, "
                "COUNT(*) FILTER (WHERE bp.completed AND bt.task_type != 'free') AS completed_count, "
                "COALESCE(u.ign, gm.ign::TEXT) AS ign, "
                "u.discord_name, u.discord_avatar, "
                "gm.guild_key, "
                "MAX(bp.last_updated) AS last_updated "
                "FROM bingo_progress bp "
                "JOIN bingo_tasks bt ON bt.id = bp.task_id "
                "LEFT JOIN users u ON u.uuid = bp.uuid "
                "LEFT JOIN LATERAL ("
                "  SELECT ign, guild_key FROM guild_members WHERE uuid = bp.uuid LIMIT 1"
                ") gm ON TRUE "
                "WHERE bp.event_id = %s "
                "GROUP BY bp.uuid, u.ign, u.discord_name, u.discord_avatar, gm.ign, gm.guild_key "
                "ORDER BY completed_count DESC, MAX(bp.last_updated) ASC",
                (event_id,),
            )
            cols = ['uuid', 'completed_count', 'ign', 'discord_name', 'discord_avatar',
                    'guild_key', 'last_updated']
            return [dict(zip(cols, r)) for r in cur.fetchall()]
