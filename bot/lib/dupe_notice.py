import threading
import time

_LOCK = threading.Lock()
_last_notice = 0.0
_last_reply = 0.0

NOTICE_WINDOW = 3.0  # both guild bots report the same dupe; post once per window
REPLY_WINDOW = 6.0   # a dupe right after a command reply is the reply itself repeating


def note_command_reply() -> None:
    global _last_reply
    with _LOCK:
        _last_reply = time.monotonic()


def should_post_duplicate_notice() -> bool:
    """True if a "Duplicate message!" embed should go to Discord now."""
    global _last_notice
    with _LOCK:
        now = time.monotonic()
        if now - _last_reply < REPLY_WINDOW:
            return False
        if now - _last_notice < NOTICE_WINDOW:
            return False
        _last_notice = now
        return True
