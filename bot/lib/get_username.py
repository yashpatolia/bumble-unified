import logging
import os

import psycopg2
from lib.fetch import request

_DSN = os.getenv("DATABASE_URL", "")


def get_username(uuid: str) -> str | None:
    """Resolve a UUID to a Minecraft username, using the local DB as a cache."""
    try:
        conn = psycopg2.connect(_DSN)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT ign FROM users WHERE uuid = %s", (uuid,))
                row = cur.fetchone()
                if row:
                    return row[0]
                ign = request(f"https://api.minecraftservices.com/minecraft/profile/lookup/{uuid}")["name"]
                cur.execute("SELECT uuid FROM users WHERE LOWER(ign) = LOWER(%s)", (ign,))
                existing = cur.fetchone()
                if existing:
                    cur.execute("UPDATE users SET ign = %s WHERE uuid = %s", (ign.lower(), uuid))
                else:
                    cur.execute("INSERT INTO users (uuid, ign) VALUES (%s, %s)", (uuid, ign.lower()))
            conn.commit()
            return ign
        finally:
            conn.close()
    except Exception as e:
        logging.error(e)
        return None
