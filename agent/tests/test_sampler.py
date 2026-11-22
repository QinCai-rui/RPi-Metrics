import asyncio
import threading
import time
from collections import namedtuple
from types import SimpleNamespace

import pytest

from agent.main import app, get_metrics, lifespan
from agent.metrics.cpu import CPUCollector
from agent.metrics import cpu
from agent.metrics.sampler import DEFAULT_INTERVALS, MetricsSampler, RateCalculator


def wait_for(predicate, timeout=2):
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() >= deadline:
            pytest.fail("timed out waiting for sampler")
        time.sleep(0.005)


def test_default_intervals_and_validation():
    assert DEFAULT_INTERVALS["cpu"] == (30, 5)
    assert DEFAULT_INTERVALS["disk"] == (60, 10)
    assert DEFAULT_INTERVALS["temperature"] == (60, 10)
    assert DEFAULT_INTERVALS["system"] == (120, 30)
    with pytest.raises(ValueError):
        MetricsSampler(intervals={"x": (0, 1)}, collectors={"x": lambda: None})


def test_rates_resets_disappearance_and_nonpositive_elapsed():
    rates = RateCalculator({"read": "read_rate", "write": "write_rate"})
    def update(values, now):
        rates.update(values, now)
        return values
    first = update({"a": {"read": 10, "write": 20}}, 1)
    assert first["a"]["read_rate"] is None
    second = update({"a": {"read": 30, "write": 50}}, 3)
    assert second["a"]["read_rate"] == 10
    assert second["a"]["write_rate"] == 15
    reset = update({"a": {"read": 1, "write": 60}}, 4)
    assert reset["a"]["read_rate"] is None
    assert reset["a"]["write_rate"] == 10
    assert update({"a": {"read": 2, "write": 61}}, 4)["a"]["read_rate"] is None
    update({}, 5)
    assert update({"a": {"read": 3, "write": 62}}, 6)["a"]["read_rate"] is None
    rates.update(None, 7)
    assert update({"a": {"read": 4, "write": 63}}, 8)["a"]["read_rate"] is None


def test_cpu_interval_calculation():
    times = namedtuple("times", "user idle iowait guest")
    assert CPUCollector._usage(None, times(1, 1, 0, 0)) is None
    assert CPUCollector._usage(times(10, 10, 0, 0), times(15, 15, 0, 0)) == 50
    assert CPUCollector._usage(times(10, 10, 0, 0), times(1, 15, 0, 0)) is None


def test_scaling_governor_supported_and_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(cpu, "CPU_SYSFS", tmp_path)
    path = tmp_path / "cpu0" / "cpufreq"
    path.mkdir(parents=True)
    (path / "scaling_governor").write_text("schedutil\n")
    assert cpu.scaling_governor(0) == "schedutil"
    assert cpu.scaling_governor(1) is None


def test_active_switch_and_no_overlapping_collection():
    calls = []
    running = threading.Lock()
    def collect():
        assert running.acquire(blocking=False)
        try:
            calls.append(time.monotonic())
            time.sleep(0.015)
            return {"count": len(calls)}
        finally:
            running.release()
    sampler = MetricsSampler(intervals={"x": (1, 0.03)}, collectors={"x": collect})
    sampler.start()
    try:
        wait_for(lambda: len(calls) == 1)
        sampler.set_active(True)
        wait_for(lambda: len(calls) >= 3)
        sampler.set_active(False)
        count = len(calls)
        time.sleep(0.08)
        assert len(calls) == count
    finally:
        sampler.stop()
    assert sampler._thread is None


def test_failure_isolated_snapshot_and_bounded_history():
    def bad():
        raise RuntimeError("broken")
    sampler = MetricsSampler(intervals={"good": (0.02, 0.01), "bad": (0.02, 0.01)},
                             collectors={"good": lambda: {"nested": [1]}, "bad": bad},
                             history_size=3)
    sampler.start()
    try:
        wait_for(lambda: len(sampler.history()) == 3)
        snapshot = sampler.snapshot()
        assert snapshot["bad"] is None
        assert snapshot["good"] == {"nested": [1]}
        assert snapshot["freshness"]["good"]["age_seconds"] >= 0
        assert snapshot["timestamp"].endswith("+00:00")
        snapshot["good"]["nested"].append(2)
        history = sampler.history()
        history.clear()
        assert sampler.snapshot()["good"] == {"nested": [1]}
        assert len(sampler.history()) == 3
    finally:
        sampler.stop()


def test_lifespan_and_cached_endpoint():
    async def check():
        async with lifespan(app):
            sampler = app.state.sampler
            wait_for(lambda: sampler.snapshot()["timestamp"] is not None)
            request = type("Request", (), {"app": app})()
            assert get_metrics(request)["freshness"]
            assert sampler._thread.is_alive()
        assert sampler._thread is None
    asyncio.run(check())


def test_endpoint_only_reads_cache():
    calls = []
    class Cached:
        def snapshot(self):
            calls.append("snapshot")
            return {"cpu": None}
    request = type("Request", (), {
        "app": type("App", (), {"state": type("State", (), {"sampler": Cached()})()})()
    })()
    assert get_metrics(request) == {"cpu": None}
    assert calls == ["snapshot"]


def test_activity_requires_loopback_and_token_and_expires():
    now = 0
    sampler = MetricsSampler(clock=lambda: now)
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(sampler=sampler, activity_token=b"test-token")),
        client=SimpleNamespace(host="127.0.0.1"),
        headers={},
    )

    def cpu_interval():
        return get_metrics(request)["freshness"]["cpu"]["interval_seconds"]

    assert cpu_interval() == 30
    request.headers["X-Fleetmuster-Activity"] = "wrong"
    assert cpu_interval() == 30
    request.headers["X-Fleetmuster-Activity"] = "test-token"
    request.client.host = "192.0.2.8"
    assert cpu_interval() == 30
    request.client.host = "127.0.0.1"
    assert cpu_interval() == 5
    now = 8
    assert cpu_interval() == 5
    request.headers.clear()
    now = 13
    assert cpu_interval() == 5
    now = 21
    assert cpu_interval() == 30
