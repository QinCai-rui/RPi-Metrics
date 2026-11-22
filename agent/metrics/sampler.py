"""Single-worker, in-memory metrics sampling."""

import copy
import logging
import math
import threading
import time
from collections import deque
from datetime import datetime, timezone

from agent.metrics.cpu import CPUCollector
from agent.metrics.disk import collect_disk
from agent.metrics.memory import collect_memory
from agent.metrics.network import collect_network
from agent.metrics.system import collect_system
from agent.metrics.temperature import collect_temperature

logger = logging.getLogger(__name__)

DEFAULT_INTERVALS = {
    "cpu": (30, 5), "memory": (30, 5), "network": (30, 5),
    "disk": (60, 10), "temperature": (60, 10), "system": (120, 30),
}


class RateCalculator:
    def __init__(self, fields):
        self.fields = fields
        self.previous = {}

    def update(self, devices, now):
        if devices is None:
            self.previous = {}
            return
        previous = self.previous
        self.previous = {}
        for name, counters in devices.items():
            old = previous.get(name)
            for counter, rate in self.fields.items():
                value = counters.get(counter)
                result = None
                if old and value is not None and old[1].get(counter) is not None:
                    elapsed = now - old[0]
                    difference = value - old[1][counter]
                    if elapsed > 0 and difference >= 0:
                        result = difference / elapsed
                counters[rate] = result
            self.previous[name] = (now, {field: counters.get(field) for field in self.fields})


class MetricsSampler:
    def __init__(self, intervals=None, history_size=120, collectors=None, clock=time.monotonic):
        self.intervals = dict(DEFAULT_INTERVALS if intervals is None else intervals)
        if any(len(pair) != 2 or any(not math.isfinite(v) or v <= 0 for v in pair)
               for pair in self.intervals.values()):
            raise ValueError("sampling intervals must be positive finite idle/active pairs")
        if history_size < 1:
            raise ValueError("history_size must be positive")
        self.collectors = collectors if collectors is not None else {
            "cpu": CPUCollector(), "memory": collect_memory, "network": collect_network,
            "disk": collect_disk, "temperature": collect_temperature, "system": collect_system,
        }
        if set(self.collectors) != set(self.intervals):
            raise ValueError("intervals and collectors must have matching names")
        self.clock = clock
        self._condition = threading.Condition()
        self._active = False
        self._active_until = 0
        self._stopping = False
        self._thread = None
        self._data = {name: None for name in self.collectors}
        self._times = {name: None for name in self.collectors}
        self._monotonic_times = {name: None for name in self.collectors}
        self._history = deque(maxlen=history_size)
        self._rates = {
            "network": RateCalculator({"bytes_sent": "upload_bytes_per_second",
                                       "bytes_received": "download_bytes_per_second"}),
            "disk": RateCalculator({"read_bytes": "read_bytes_per_second",
                                    "write_bytes": "write_bytes_per_second"}),
        }

    def start(self):
        with self._condition:
            if self._thread is not None:
                raise RuntimeError("sampler already started")
            self._stopping = False
            self._thread = threading.Thread(target=self._run, name="metrics-sampler", daemon=True)
            self._thread.start()

    def stop(self):
        with self._condition:
            thread = self._thread
            if thread is None:
                return
            self._stopping = True
            self._condition.notify_all()
        thread.join()
        with self._condition:
            self._thread = None

    def set_active(self, active):
        with self._condition:
            self._active = bool(active)
            self._condition.notify_all()

    def keep_active(self, seconds):
        with self._condition:
            now = self.clock()
            was_active = self._active or now < self._active_until
            self._active_until = now + seconds
            if not was_active:
                self._condition.notify_all()

    def snapshot(self):
        with self._condition:
            now = self.clock()
            active = self._active or now < self._active_until
            result = copy.deepcopy(self._data)
            result["timestamp"] = max((t for t in self._times.values() if t), default=None)
            result["freshness"] = {
                name: {"sampled_at": self._times[name],
                       "age_seconds": max(0, now - sampled) if sampled is not None else None,
                       "interval_seconds": self.intervals[name][active]}
                for name, sampled in self._monotonic_times.items()
            }
            return result

    def history(self):
        with self._condition:
            return copy.deepcopy(list(self._history))

    def _run(self):
        # The previous attempted time also prevents a failing collector from spinning.
        attempted = {name: None for name in self.collectors}
        while True:
            with self._condition:
                if self._stopping:
                    return
                now = self.clock()
                active = self._active or now < self._active_until
                due = [name for name, last in attempted.items()
                       if last is None or now >= last + self.intervals[name][active]]
                if not due:
                    delay = min(last + self.intervals[name][active] - now
                                for name, last in attempted.items())
                    self._condition.wait(timeout=max(0, delay))
                    continue
            for name in due:
                with self._condition:
                    if self._stopping:
                        return
                attempted[name] = self.clock()
                try:
                    value = self.collectors[name]()
                    sampled = self.clock()
                    if name == "network":
                        self._rates[name].update(value.get("interfaces") if value else None, sampled)
                    elif name == "disk":
                        self._rates[name].update(value.get("io") if value else None, sampled)
                except Exception:
                    logger.warning("Metrics collector %s failed", name, exc_info=True)
                    value = None
                    sampled = self.clock()
                    if name in self._rates:
                        self._rates[name].update(None, sampled)
                stamp = datetime.now(timezone.utc).isoformat()
                with self._condition:
                    self._data[name] = value
                    self._times[name] = stamp
                    self._monotonic_times[name] = sampled
                    self._history.append({"collector": name, "timestamp": stamp,
                                          "value": copy.deepcopy(value)})
