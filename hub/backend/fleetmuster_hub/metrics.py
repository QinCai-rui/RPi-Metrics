import json
import math
import time
from datetime import datetime, timezone

COLLECTORS = ("cpu", "memory", "disk", "network", "temperature", "system")
DAY = 86400


def timestamp(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat() if value is not None else None


def number(value):
    return value if type(value) in (int, float) and math.isfinite(value) else None


def total(rows, field):
    values = [value for row in rows if (value := number(row.get(field))) is not None]
    return sum(values) if values else None


def peak(rows, field):
    return max((value for row in rows if (value := number(row.get(field))) is not None), default=None)


def readings(collector, value):
    """Numeric readings shared by history and guest metrics, without host identifiers."""
    value = value or {}
    if collector == "cpu":
        return {"cpu_percent": value.get("usage_percent")}
    if collector == "memory":
        return {f"{name}_percent": (value.get(name) or {}).get("usage_percent")
                for name in ("ram", "swap")}
    if collector == "disk":
        return {"disk_percent": peak(value.get("filesystems") or [], "usage_percent")}
    if collector == "network":
        interfaces = [row for row in (value.get("interfaces") or {}).values()
                      if row.get("type") not in {"loopback", "virtual"}]
        return {f"{direction}_bytes_per_second": total(interfaces, f"{direction}_bytes_per_second")
                for direction in ("upload", "download")}
    if collector == "temperature":
        return {"temperature_celsius": peak(
            (row for sensor in value.values() for row in sensor), "current_celsius"
        )}
    return {}


def sample_time(value):
    if not isinstance(value, str):
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("Collector timestamp must include its timezone")
    return parsed.timestamp()


def record_snapshot(db, host_id, snapshot, now):
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("freshness"), dict):
        raise ValueError("Agent did not return a metrics snapshot")
    snapshot = {key: snapshot.get(key) for key in (*COLLECTORS, "freshness", "timestamp")}
    samples = []
    summary = {}
    freshness = {}
    for collector in COLLECTORS:
        value = snapshot[collector]
        meta = snapshot["freshness"].get(collector, {})
        if (value is not None and not isinstance(value, dict)) or not isinstance(meta, dict):
            raise ValueError("Agent returned an invalid collector snapshot")
        sampled = sample_time(meta.get("sampled_at"))
        freshness[collector] = {
            "sampled_at": timestamp(sampled),
            "interval_seconds": number(meta.get("interval_seconds")),
        }
        values = {key: number(reading) for key, reading in readings(collector, value).items()}
        summary.update(values)
        if values and sampled is not None and now - 7 * DAY <= sampled <= now + 5:
            # Keep null readings for observed gaps. Only numeric readings feed averages.
            samples.append((collector, sampled, values))
    snapshot["freshness"] = freshness
    snapshot["summary"] = summary
    hostname = (snapshot["system"] or {}).get("hostname")
    with db.connect(write=True) as connection:
        connection.execute(
            """UPDATE hosts SET last_contact = ?, online = 1, snapshot = ?,
            observed_hostname = coalesce(?, observed_hostname) WHERE id = ?""",
            (now, json.dumps(snapshot, allow_nan=False), hostname if isinstance(hostname, str) else None, host_id),
        )
        for collector, sampled, values in samples:
            result = connection.execute(
                "INSERT OR IGNORE INTO metric_samples VALUES (?, ?, ?, ?)",
                (host_id, collector, sampled, json.dumps(values)),
            )
            if not result.rowcount:
                continue
            hour = int(sampled // 3600) * 3600
            connection.executemany(
                """INSERT INTO metric_hourly VALUES (?, ?, ?, ?, 1)
                ON CONFLICT (host_id, hour, metric) DO UPDATE
                SET total = total + excluded.total, count = count + 1""",
                [(host_id, metric, hour, reading) for metric, reading in values.items() if reading is not None],
            )


def prune_history(connection, now):
    connection.execute("DELETE FROM metric_samples WHERE sampled_at < ?", (now - 7 * DAY,))
    connection.execute("DELETE FROM metric_hourly WHERE hour < ?", (int((now - 90 * DAY) // 3600) * 3600,))


def history(connection, host_id, hours, now):
    since = now - hours * 3600
    if hours <= 24:
        rows = connection.execute(
            """SELECT sampled_at, values_json FROM metric_samples
            WHERE host_id = ? AND sampled_at >= ? ORDER BY sampled_at""", (host_id, since),
        )
        points = {}
        for row in rows:
            for metric, value in json.loads(row["values_json"]).items():
                points.setdefault(metric, []).append([timestamp(row["sampled_at"]), value])
        return {"resolution": "sample", "series": points}
    rows = connection.execute(
        """SELECT hour, metric, total / count AS average FROM metric_hourly
        WHERE host_id = ? AND hour >= ? ORDER BY hour""", (host_id, int(since // 3600) * 3600),
    )
    points = {}
    for row in rows:
        points.setdefault(row["metric"], []).append([timestamp(row["hour"]), row["average"]])
    return {"resolution": "hour", "series": points}


def host_info(host, role, poll_interval, now=None):
    now = time.time() if now is None else now
    contacted = host["last_contact"]
    online = bool(host["online"] and contacted is not None and now - contacted <= poll_interval + 10)
    return {
        "id": host["id"], "name": host["name"], "kind": host["kind"],
        "observed_hostname": host["observed_hostname"] if role != "guest" else None,
        "status": "online" if online else "stale" if contacted is not None else "unavailable",
        "last_contact": timestamp(contacted),
    }


def cached_metrics(host, info, role, poll_interval):
    now = time.time()
    snapshot = json.loads(host["snapshot"]) if host["snapshot"] else {}
    freshness = {}
    for collector in COLLECTORS:
        meta = snapshot.get("freshness", {}).get(collector, {})
        sampled = sample_time(meta.get("sampled_at"))
        interval = meta.get("interval_seconds")
        age = max(0, now - sampled) if sampled is not None else None
        if age is None or snapshot.get(collector) is None:
            status = "unavailable"
        elif info["status"] != "online" or (interval and age > 2 * interval + poll_interval):
            status = "stale"
        else:
            status = "current"
        freshness[collector] = {**meta, "age_seconds": age, "status": status}
    result = {"host": info, "freshness": freshness, "summary": snapshot.get("summary", {})}
    if role != "guest":
        result["collectors"] = {name: snapshot.get(name) for name in COLLECTORS}
    return result
