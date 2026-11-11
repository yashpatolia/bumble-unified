import threading
import time

_LOCK = threading.Lock()
_last_notice = 0.0
_last_command = 0.0

NOTICE_WINDOW = 3.0    # both guild bots report the same dupe; post once per window
COMMAND_WINDOW = 12.0  # a repeated command dupes twice (the command, then its reply): post once


def note_command() -> None:
    """A dot-command was just run; the dupe notices it causes count as one."""
    global _last_command
    with _LOCK:
        _last_command = time.monotonic()


def should_post_duplicate_notice() -> bool:
    """True if a "Duplicate message!" embed should go to Discord now."""
    global _last_notice
    with _LOCK:
        now = time.monotonic()
        if now - _last_notice < NOTICE_WINDOW:
            return False
        if _last_notice >= _last_command and now - _last_command < COMMAND_WINDOW:
            return False  # this command already got its notice
        _last_notice = now
        return True
