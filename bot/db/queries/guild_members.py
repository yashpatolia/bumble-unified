import time as _time
from typing import Optional

from psycopg2.extras import Json, execute_values

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

            # Batch upsert, preserving stats columns. De-dupe by lowercased IGN first —
            # `ign` is CITEXT, so `ON CONFLICT (guild_key, ign)` matches case-insensitively,
            # and a single INSERT..ON CONFLICT statement can't touch the same conflict-target
            # row twice (raises CardinalityViolation). Last occurrence wins.
            if members:
                deduped = {}
                for m in members:
                    deduped[m['ign'].lower()] = m
                execute_values(
                    cur,
                    "INSERT INTO guild_members (guild_key, ign, uuid, rank) VALUES %s "
                    "ON CONFLICT (guild_key, ign) DO UPDATE SET "
                    "uuid = COALESCE(EXCLUDED.uuid, guild_members.uuid), "
                    "rank = EXCLUDED.rank",
                    [(guild_key, m['ign'], m.get('uuid') or None, m.get('rank', '')) for m in deduped.values()],
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

    def record_level_snapshot(self, guild_key: str, ign: str, uuid: Optional[str], level,
                              catacombs_xp: Optional[float] = None, slayer_xp: Optional[dict] = None) -> None:
        """Inserts one snapshot per member per UTC calendar day. If today's row already exists it is
        only topped up with Catacombs/slayer XP it was missing (rows from before those were tracked)."""
        with self._cursor() as cur:
            today_start = int(_time.time()) - (int(_time.time()) % 86400)
            cur.execute(
                "SELECT 1 FROM guild_member_level_history "
                "WHERE guild_key = %s AND LOWER(ign) = LOWER(%s) AND recorded_at >= %s LIMIT 1",
                (guild_key, ign, today_start),
            )
            if cur.fetchone():
                if catacombs_xp is not None or slayer_xp is not None:
                    cur.execute(
                        "UPDATE guild_member_level_history SET catacombs_xp = COALESCE(catacombs_xp, %s), "
                        "slayer_xp = COALESCE(slayer_xp, %s) "
                        "WHERE guild_key = %s AND LOWER(ign) = LOWER(%s) AND recorded_at >= %s",
                        (catacombs_xp, Json(slayer_xp) if slayer_xp is not None else None, guild_key, ign, today_start),
                    )
                return
            cur.execute(
                "INSERT INTO guild_member_level_history (guild_key, ign, uuid, level, recorded_at, catacombs_xp, slayer_xp) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (guild_key, ign, uuid, level, int(_time.time()), catacombs_xp,
                 Json(slayer_xp) if slayer_xp is not None else None),
            )

    def get_member_history(self, guild_key: str, ign: str, days: int = 90) -> list:
        """[(recorded_at, level, catacombs_xp, slayer_xp_dict), ...] oldest first, for the member page."""
        since = int(_time.time()) - days * 86400
        with self._cursor() as cur:
            cur.execute(
                "SELECT recorded_at, level, catacombs_xp, slayer_xp FROM guild_member_level_history "
                "WHERE guild_key = %s AND LOWER(ign) = LOWER(%s) AND recorded_at >= %s ORDER BY recorded_at",
                (guild_key, ign, since),
            )
            return cur.fetchall()

    def get_member_by_uuid(self, uuid: str) -> Optional[tuple]:
        """(guild_key, rank) of the guild a UUID is on, or None."""
        with self._cursor() as cur:
            cur.execute("SELECT guild_key, rank FROM guild_members WHERE uuid = %s LIMIT 1", (uuid,))
            return cur.fetchone()

    def get_member_row(self, guild_key: str, ign: str) -> Optional[tuple]:
        """Same columns as get_guild_members, for one member."""
        with self._cursor() as cur:
            cur.execute(
                "SELECT gm.ign::TEXT, gm.rank, gm.skyblock_level, gm.last_login, gm.uuid, "
                "u.discord_name, u.discord_id, u.discord_avatar, gm.stats_fetched_at "
                "FROM guild_members gm LEFT JOIN users u ON u.uuid = gm.uuid "
                "WHERE gm.guild_key = %s AND LOWER(gm.ign) = LOWER(%s)",
                (guild_key, ign),
            )
            return cur.fetchone()

    def get_average_level_trend(self, guild_key: str, days: int = 30, exclude_igns: tuple = ()) -> list:
        """Returns [(day_start_unix, avg_level, member_count), ...] oldest first, one entry per UTC day
        for the last `days` days. Each day averages every current member's latest snapshot recorded
        before that day ended; members with no snapshot yet that day are left out (history only
        starts once a member has been refreshed), so member_count shows how complete the point is.
        `exclude_igns` (any case) drops accounts such as the guild bots from the average."""
        now = int(_time.time())
        today_start = now - (now % 86400)
        first_day = today_start - (days - 1) * 86400
        # Look 30 days before the window so members refreshed less often still have a baseline.
        since = first_day - 30 * 86400
        with self._cursor() as cur:
            cur.execute(
                "SELECT h.ign::TEXT, h.level, h.recorded_at FROM guild_member_level_history h "
                "JOIN guild_members m ON m.guild_key = h.guild_key AND m.ign = h.ign "
                "WHERE h.guild_key = %s AND h.level IS NOT NULL AND h.recorded_at >= %s "
                "  AND LOWER(h.ign::TEXT) <> ALL(%s) "
                "ORDER BY h.recorded_at",
                (guild_key, since, [n.lower() for n in exclude_igns]),
            )
            rows = cur.fetchall()
        by_member: dict = {}
        for ign, level, recorded_at in rows:
            by_member.setdefault(ign, []).append((recorded_at, level))
        points = []
        for i in range(days):
            day_start = first_day + i * 86400
            day_end = day_start + 86400
            levels = []
            for snaps in by_member.values():
                latest = None
                for recorded_at, level in snaps:
                    if recorded_at >= day_end:
                        break
                    latest = level
                if latest is not None:
                    levels.append(latest)
            if levels:
                points.append((day_start, sum(levels) / len(levels), len(levels)))
        return points

    def get_level_gain_90d(self, guild_key: str) -> dict:
        return self.get_level_gains(guild_key, 90)

    def get_level_gains(self, guild_key: str, days: int) -> dict:
        """Returns {ign: (level_as_of_anchor, recorded_at)} — the anchor snapshot closest to `days`
        days ago: the most recent snapshot at or before the cutoff if one exists (so the gain keeps
        showing indefinitely once 90 days of history has accumulated, instead of disappearing when
        the oldest row ages out of a strict window), else the oldest snapshot recorded at all
        (cold-start period, under 90 days of history — recorded_at lets callers show how many days
        the gain actually covers while under 90)."""
        cutoff = int(_time.time()) - days * 86400
        with self._cursor() as cur:
            cur.execute(
                "SELECT DISTINCT ON (ign) ign::TEXT, level, recorded_at FROM guild_member_level_history "
                "WHERE guild_key = %s "
                "ORDER BY ign, "
                "  (recorded_at > %s), "  # false (0) sorts first: prefer rows at/before cutoff
                "  CASE WHEN recorded_at <= %s THEN -recorded_at ELSE recorded_at END ASC",
                (guild_key, cutoff, cutoff),
            )
            return {row[0]: (row[1], row[2]) for row in cur.fetchall()}
