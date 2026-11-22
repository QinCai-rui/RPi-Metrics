# Fleetmuster agent metrics

Run from the repository root with `uvicorn agent.main:app`. The agent starts one
sampler per process, so run a single worker unless separate per-worker histories
are acceptable.

`GET /api/v1/metrics` returns the latest cached values. `timestamp` is the most
recent collection attempt, and `freshness` contains each collector's UTC
`sampled_at`, monotonic `age_seconds`, and current `interval_seconds`. A failed
or unsupported measurement is `null`; CPU usage and I/O rates are also `null`
until a second counter reading. History is bounded in memory and is not persisted.

Intervals are configured with the `MetricsSampler(intervals=...)` constructor;
each collector takes an `(idle_seconds, active_seconds)` pair. Call
`app.state.sampler.set_active(True)` or `set_active(False)` to switch modes
without restarting. This is an internal interface for future hub integration,
not an HTTP endpoint. Temperature readings are grouped by sensor name. The
system `power_profile` contains `name` and `source`, or is `null`; it is
independent of CPU frequency governors. `cpu.per_core_scaling_governor` lists
the governor for each logical CPU, with `null` when unavailable.

Run tests from the repository root:

```sh
uv run --with pytest --with fastapi --with psutil python -m pytest agent/tests
```
