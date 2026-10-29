"""Wait for a specific line of Minecraft chat from async code.

Mineflayer callbacks run on the JSPyBridge thread, so a waiter is a predicate plus an
asyncio future; cogs/bridge/message_handler.py feeds every `messagestr` line through
feed(), which resolves the first matching future on the event loop."""
import asyncio
from typing import Callable, Optional


def feed(state, message: str, loop: asyncio.AbstractEventLoop) -> None:
    for predicate, future in list(state.chat_waiters):
        if not future.done() and predicate(message):
            loop.call_soon_threadsafe(_resolve, future, message)


def _resolve(future: asyncio.Future, message: str) -> None:
    if not future.done():
        future.set_result(message)


async def wait_for_chat(state, predicate: Callable[[str], bool], timeout: float) -> Optional[str]:
    """Returns the first chat line matching `predicate`, or None after `timeout` seconds."""
    future = asyncio.get_running_loop().create_future()
    waiter = (predicate, future)
    state.chat_waiters.append(waiter)
    try:
        return await asyncio.wait_for(future, timeout)
    except asyncio.TimeoutError:
        return None
    finally:
        state.chat_waiters.remove(waiter)
