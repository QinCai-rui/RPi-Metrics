import asyncio
import logging
import random
import sqlite3
import threading
import time

import httpx

from .metrics import prune_history, record_snapshot

logger = logging.getLogger(__name__)


def agent_client(settings):
    return httpx.AsyncClient(base_url=settings.agent_url, timeout=4, trust_env=False)


class Poller:
    def __init__(self, settings, db, host_id):
        self.settings = settings
        self.db = db
        self.host_id = host_id
        self.loop = asyncio.get_running_loop()
        self.wake = asyncio.Event()
        self.stop = asyncio.Event()
        self.lock = threading.Lock()
        self.active_until = 0

    def view(self, host_id):
        if host_id != self.host_id:
            return
        with self.lock:
            was_idle = time.monotonic() >= self.active_until
            self.active_until = time.monotonic() + 8
        if was_idle:
            self.loop.call_soon_threadsafe(self.wake.set)

    def failed(self):
        with self.db.connect(write=True) as connection:
            connection.execute("UPDATE hosts SET online = 0 WHERE id = ?", (self.host_id,))

    def prune(self):
        with self.db.connect(write=True) as connection:
            prune_history(connection, time.time())

    async def run(self):
        failures = 0
        next_prune = 0
        async with agent_client(self.settings) as client:
            while not self.stop.is_set():
                self.wake.clear()
                started = time.monotonic()
                try:
                    if started >= next_prune:
                        await asyncio.to_thread(self.prune)
                        next_prune = started + 3600
                    headers = {}
                    if self.settings.activity_token and time.monotonic() < self.active_until:
                        headers["X-Fleetmuster-Activity"] = self.settings.activity_token
                    response = await client.get("/api/v1/metrics", headers=headers)
                    response.raise_for_status()
                    await asyncio.to_thread(
                        record_snapshot, self.db, self.host_id, response.json(), time.time()
                    )
                    failures = 0
                except sqlite3.Error:
                    if not failures:
                        logger.exception("Could not save local metrics")
                    failures = min(failures + 1, 10)
                except (httpx.HTTPError, ValueError, TypeError, AttributeError, OverflowError) as exc:
                    if not failures:
                        logger.warning("Could not refresh local metrics: %s", type(exc).__name__)
                    failures = min(failures + 1, 10)
                    try:
                        await asyncio.to_thread(self.failed)
                    except sqlite3.Error:
                        logger.exception("Could not save local agent status")

                jitter = random.uniform(0.8, 1.2)
                while not self.stop.is_set():
                    if failures:
                        # Opening a dashboard must not reset the outage backoff.
                        delay = min(300, self.settings.active_poll * 2 ** (failures - 1) * jitter)
                    else:
                        delay = (self.settings.active_poll if time.monotonic() < self.active_until
                                 else self.settings.idle_poll)
                    try:
                        await asyncio.wait_for(self.wake.wait(), max(0, started + delay - time.monotonic()))
                    except TimeoutError:
                        break
                    self.wake.clear()
