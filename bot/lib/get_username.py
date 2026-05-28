import logging

from lib.fetch import request


def get_username(uuid: str) -> str | None:
    """Resolve a UUID to a Minecraft username, using the local DB as a cache."""
    from db import manager
    try:
        with manager._cursor() as cur:
            cur.execute("SELECT ign FROM users WHERE uuid = %s", (uuid,))
            row = cur.fetchone()
            if row and row[0]:
                return row[0]
        ign = request(f"https://api.minecraftservices.com/minecraft/profile/lookup/{uuid}")["name"]
        with manager._cursor() as cur:
            cur.execute("SELECT uuid FROM users WHERE LOWER(ign) = LOWER(%s)", (ign,))
            existing = cur.fetchone()
            if existing:
                cur.execute("UPDATE users SET ign = %s WHERE uuid = %s", (ign, uuid))
            else:
                cur.execute("INSERT INTO users (uuid, ign) VALUES (%s, %s)", (uuid, ign))
        return ign
    except Exception as e:
        logging.error(e)
        return None
