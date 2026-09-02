from __future__ import annotations

import asyncio
import threading
from concurrent.futures import Future
from typing import Coroutine


class AsyncLoopRunner:
    """Runs one persistent asyncio event loop on a background thread.

    httpx.AsyncClient binds its connection pool to whichever event loop first
    uses it; calling asyncio.run() per request creates and closes a new loop
    each time, so a second call fails with "Event loop is closed". Routing
    every coroutine through this single long-lived loop keeps the client and
    its loop matched for the app's lifetime.
    """

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run, daemon=True, name="py-crow-async")
        self._thread.start()

    def _run(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def submit(self, coro: Coroutine) -> Future:
        return asyncio.run_coroutine_threadsafe(coro, self._loop)

    def run_sync(self, coro: Coroutine, timeout: float | None = None):
        return self.submit(coro).result(timeout=timeout)

    def stop(self) -> None:
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=2)
        self._loop.close()
