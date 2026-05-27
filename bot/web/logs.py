import logging
from datetime import datetime
from threading import Lock

MAX_HISTORY = 500


class LogBroadcaster:
    """Thread-safe append-only log store. WebSocket handlers poll get_after()."""

    def __init__(self):
        self._records: list[dict] = []
        self._lock = Lock()

    def broadcast(self, record: dict) -> None:
        with self._lock:
            self._records.append(record)
            if len(self._records) > MAX_HISTORY:
                del self._records[:len(self._records) - MAX_HISTORY]

    def snapshot(self) -> list:
        with self._lock:
            return list(self._records)

    def get_after(self, offset: int) -> list:
        with self._lock:
            return list(self._records[offset:])

    def size(self) -> int:
        with self._lock:
            return len(self._records)


broadcaster = LogBroadcaster()


class WebLogHandler(logging.Handler):
    """Writes every log record directly into the broadcaster store."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            broadcaster.broadcast({
                "time": datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S"),
                "level": record.levelname,
                "message": record.getMessage(),
                "source": f"{record.filename}:{record.lineno}",
            })
        except Exception:
            pass
