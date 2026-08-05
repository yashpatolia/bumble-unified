from contextlib import contextmanager

import psycopg2
import psycopg2.pool


class BaseQueries:
    """Shared connection pool + cursor contextmanager used by every domain query mixin."""

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
