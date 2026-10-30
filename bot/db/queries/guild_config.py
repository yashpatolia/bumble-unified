import datetime as _dt
from typing import Optional

from psycopg2.extras import Json

from db.base import BaseQueries


class GuildConfigQueries(BaseQueries):
    """Panel-editable per-guild settings (`guild_config`): rank level requirements and attention thresholds."""

    def get_guild_config(self, guild_key: str) -> Optional[dict]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT rank_requirements, attention, updated_by, updated_at, activity_tiers, rank_roles FROM guild_config WHERE guild_key = %s",
                (guild_key,),
            )
            row = cur.fetchone()
        if not row:
            return None
        return {"rank_requirements": row[0] or {}, "attention": row[1] or {}, "updated_by": row[2], "updated_at": row[3], "activity_tiers": row[4] or {}, "rank_roles": row[5] or {}}

    def set_guild_config(self, guild_key: str, rank_requirements: dict, attention: dict, activity_tiers: dict, updated_by: str) -> None:
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO guild_config (guild_key, rank_requirements, attention, activity_tiers, updated_by, updated_at) "
                "VALUES (%s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (guild_key) DO UPDATE SET rank_requirements = EXCLUDED.rank_requirements, "
                "attention = EXCLUDED.attention, activity_tiers = EXCLUDED.activity_tiers, updated_by = EXCLUDED.updated_by, updated_at = EXCLUDED.updated_at",
                (guild_key, Json(rank_requirements), Json(attention), Json(activity_tiers), updated_by, _dt.datetime.now(_dt.timezone.utc)),
            )

    def set_rank_roles(self, guild_key: str, rank_roles: dict, updated_by: str) -> None:
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO guild_config (guild_key, rank_roles, updated_by, updated_at) VALUES (%s, %s, %s, %s) "
                "ON CONFLICT (guild_key) DO UPDATE SET rank_roles = EXCLUDED.rank_roles, "
                "updated_by = EXCLUDED.updated_by, updated_at = EXCLUDED.updated_at",
                (guild_key, Json(rank_roles), updated_by, _dt.datetime.now(_dt.timezone.utc)),
            )

    def get_minecraft_version(self, guild_key: str) -> Optional[str]:
        with self._cursor() as cur:
            cur.execute("SELECT minecraft_version FROM guild_config WHERE guild_key = %s", (guild_key,))
            row = cur.fetchone()
        return row[0] if row else None

    def set_minecraft_version(self, guild_key: str, version: Optional[str], updated_by: str) -> None:
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO guild_config (guild_key, minecraft_version, updated_by, updated_at) VALUES (%s, %s, %s, %s) "
                "ON CONFLICT (guild_key) DO UPDATE SET minecraft_version = EXCLUDED.minecraft_version, "
                "updated_by = EXCLUDED.updated_by, updated_at = EXCLUDED.updated_at",
                (guild_key, version, updated_by, _dt.datetime.now(_dt.timezone.utc)),
            )
