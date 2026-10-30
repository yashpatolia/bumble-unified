import datetime as _dt
from typing import Optional

from psycopg2.extras import Json

from db.base import BaseQueries


class SettingsQueries(BaseQueries):
    """Shared, not per-guild, panel-edited settings (`bot_settings`): one JSON value per key."""

    def get_setting(self, key: str) -> Optional[dict]:
        """Returns {"value", "updated_by", "updated_at"} or None when the key was never saved."""
        with self._cursor() as cur:
            cur.execute("SELECT value, updated_by, updated_at FROM bot_settings WHERE key = %s", (key,))
            row = cur.fetchone()
        if not row:
            return None
        return {"value": row[0] or {}, "updated_by": row[1], "updated_at": row[2]}

    def set_setting(self, key: str, value: dict, updated_by: str) -> None:
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO bot_settings (key, value, updated_by, updated_at) VALUES (%s, %s, %s, %s) "
                "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, "
                "updated_by = EXCLUDED.updated_by, updated_at = EXCLUDED.updated_at",
                (key, Json(value), updated_by, _dt.datetime.now(_dt.timezone.utc)),
            )
