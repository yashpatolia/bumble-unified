import logging

from lib.fetch import request


def get_uuid(username: str) -> str | None:
    """Resolve a Minecraft username to a UUID, using the local DB as a cache."""
    from db import manager
    try:
        with manager._cursor() as cur:
            cur.execute("SELECT uuid FROM users WHERE LOWER(ign) = LOWER(%s)", (username,))
            row = cur.fetchone()
            if row and row[0]:
                return row[0]
        uuid = request(f"https://api.mojang.com/users/profiles/minecraft/{username}")["id"]
        with manager._cursor() as cur:
            cur.execute("SELECT ign FROM users WHERE uuid = %s", (uuid,))
            existing = cur.fetchone()
            if existing:
                cur.execute("UPDATE users SET ign = %s WHERE uuid = %s", (username, uuid))
            else:
                cur.execute("INSERT INTO users (uuid, ign) VALUES (%s, %s)", (uuid, username))
        return uuid
    except Exception as e:
        logging.error(e)
        return None
