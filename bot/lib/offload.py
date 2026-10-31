"""Run blocking work off the Mineflayer callback thread.

Mineflayer `On()`/`Once()` callbacks run on JSPyBridge's loop thread, which is also the
thread that reads every reply coming back from Node. If a callback blocks (a Discord
webhook rate limit, a slow Hypixel or Mojang request, a DB stall), no reply can be read,
so every `bot.chat()` or property access from any thread times out ("Timed out accessing
'chat'") and Node gives up on Python after 100s. Callbacks should therefore do only cheap
work inline and hand everything else to offload().

Each lane is a single worker thread, so work submitted to one lane runs in order (chat
relays must not be reordered) while a stall in one lane never blocks the bridge thread
or the other lanes.
"""
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor

_lanes: dict[str, ThreadPoolExecutor] = {}
_lanes_lock = threading.Lock()
# lane -> (task name, monotonic start time) of the task a lane is running right now
_running: dict[str, tuple[str, float]] = {}


def _lane(name: str) -> ThreadPoolExecutor:
    with _lanes_lock:
        if name not in _lanes:
            _lanes[name] = ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"offload-{name}")
        return _lanes[name]


def offload(lane: str, fn, *args, **kwargs) -> None:
    """Run fn(*args, **kwargs) on the named lane's worker thread. Never raises into the caller."""
    def run() -> None:
        _running[lane] = (getattr(fn, "__name__", repr(fn)), time.monotonic())
        try:
            fn(*args, **kwargs)
        except Exception:
            logging.exception(f"[offload/{lane}] task failed")
        finally:
            _running.pop(lane, None)

    _lane(lane).submit(run)


def stalled_lanes(older_than: float) -> list[tuple[str, str, float]]:
    """Lanes whose current task has been running longer than `older_than` seconds, as (lane, task, seconds)."""
    now = time.monotonic()
    return [(lane, task, now - started) for lane, (task, started) in list(_running.items()) if now - started > older_than]
