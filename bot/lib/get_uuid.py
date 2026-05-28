import logging
import os

import psycopg2
from lib.fetch import request

_DSN = os.getenv("DATABASE_URL", "")


def get_uuid(username: str) -> str | None:
    """Resolve a Minecraft username to a UUID, using the local DB as a cache."""
    try:
        conn = psycopg2.connect(_DSN)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT uuid FROM users WHERE LOWER(ign) = LOWER(%s)", (username,))
                row = cur.fetchone()
                if row:
                    return row[0]
                uuid = request(f"https://api.mojang.com/users/profiles/minecraft/{username}")["id"]
                cur.execute("SELECT ign FROM users WHERE uuid = %s", (uuid,))
                existing = cur.fetchone()
                if existing:
                    cur.execute("UPDATE users SET ign = %s WHERE uuid = %s", (username, uuid))
                else:
                    cur.execute("INSERT INTO users (uuid, ign) VALUES (%s, %s)", (uuid, username))
            conn.commit()
            return uuid
        finally:
            conn.close()
    except Exception as e:
        logging.error(e)
        return None
