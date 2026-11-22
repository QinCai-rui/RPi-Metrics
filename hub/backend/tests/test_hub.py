import time
from contextlib import closing

import httpx
import pytest
from fastapi.testclient import TestClient

from fleetmuster_hub import app, cli
from fleetmuster_hub.auth import COOKIE
from fleetmuster_hub.config import Settings
from fleetmuster_hub.db import Database
from fleetmuster_hub.metrics import DAY, history, prune_history, record_snapshot, timestamp

API = "/api/v1"
CSRF = {"X-Fleetmuster-Request": "1"}
ADMIN = {"username": "local-admin", "password": "initial-admin-password"}


class Agent:
    available = True
    sampled_at = None
    cpu = None

    def snapshot(self):
        return {
            "cpu": {"usage_percent": self.cpu},
            "system": {"hostname": "native-pi"},
            "network": {"interfaces": {
                "eth0": {"type": "physical", "ipv4_addresses": ["192.0.2.8"],
                         "download_bytes_per_second": 1048576, "upload_bytes_per_second": 0},
                "docker0": {"type": "virtual", "download_bytes_per_second": 1048576,
                            "upload_bytes_per_second": 1048576},
            }},
            "freshness": {name: {"sampled_at": timestamp(self.sampled_at), "interval_seconds": 30}
                          for name in ("system", "cpu", "network")},
        }

    def client(self, settings):
        def respond(request):
            if not self.available:
                raise httpx.ConnectError("Agent offline", request=request)
            if request.url.path == "/health":
                return httpx.Response(200, json={"status": "ok"})
            assert request.url.path == "/api/v1/metrics"
            return httpx.Response(200, json=self.snapshot())

        return httpx.AsyncClient(base_url=settings.agent_url, transport=httpx.MockTransport(respond))


@pytest.fixture
def hub(tmp_path, monkeypatch):
    settings = Settings(tmp_path / "state", idle_poll=0.1, active_poll=0.05)
    db = Database(settings.data_dir)
    agent = Agent()
    agent.sampled_at = time.time()
    monkeypatch.setattr(cli, "agent_client", agent.client)
    monkeypatch.setattr("fleetmuster_hub.polling.agent_client", agent.client)
    monkeypatch.setattr("builtins.input", lambda prompt: ADMIN["username"])
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt: ADMIN["password"])
    return settings, db, agent


def login(client, credentials=ADMIN):
    response = client.post(API + "/login", json=credentials, headers=CSRF)
    assert response.status_code == 200, response.text
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=strict" in response.headers["set-cookie"]
    return client.cookies[COOKIE]


def get(client, path):
    response = client.get(API + path)
    assert response.status_code == 200, response.text
    return response.json()


def wait_for_status(client, host_id, status):
    deadline = time.monotonic() + 3
    while True:
        metrics = get(client, f"/hosts/{host_id}/metrics")
        if metrics["host"]["status"] == status:
            return metrics
        assert time.monotonic() < deadline, metrics
        time.sleep(0.02)


def test_initialize_restart_outage_and_recovery(hub, monkeypatch):
    settings, db, agent = hub
    agent.available = False
    with pytest.raises(RuntimeError, match="Start the native fleetmuster agent"):
        cli.initialize(settings, db)
    assert not db.path.exists()
    agent.available = True
    cli.initialize(settings, db)
    assert db.path.stat().st_mode & 0o077 == 0

    with TestClient(app.create_app(settings)) as client:
        token = login(client)
        host, = get(client, "/hosts")
        assert host["name"] == "localhost"
        host_id = host["id"]
        metrics = wait_for_status(client, host_id, "online")
        assert metrics["host"]["observed_hostname"] == "native-pi"
        assert metrics["summary"]["cpu_percent"] is None
        assert metrics["summary"]["upload_bytes_per_second"] == 0
        assert metrics["freshness"]["temperature"]["status"] == "unavailable"
        before = get(client, f"/hosts/{host_id}/history")
        assert before["series"]["cpu_percent"] == [[timestamp(agent.sampled_at), None]]
        agent.available = False
        degraded = wait_for_status(client, host_id, "stale")
        assert degraded["host"]["last_contact"] is not None
        assert degraded["summary"] == metrics["summary"]
        assert degraded["freshness"]["network"]["status"] == "stale"

    def unexpected_prompt(prompt):
        pytest.fail("Repeated init prompted for a new admin")

    monkeypatch.setattr("builtins.input", unexpected_prompt)
    cli.initialize(settings, db)
    with TestClient(app.create_app(settings), cookies={COOKIE: token}) as client:
        assert get(client, "/me")["username"] == ADMIN["username"]
        assert [host["id"] for host in get(client, "/hosts")] == [host_id]
        metrics = wait_for_status(client, host_id, "stale")
        assert metrics["host"]["last_contact"] == degraded["host"]["last_contact"]
        assert get(client, f"/hosts/{host_id}/history") == before
        agent.cpu = 22.0
        agent.sampled_at = time.time()
        agent.available = True
        assert wait_for_status(client, host_id, "online")["summary"]["cpu_percent"] == 22.0


def test_host_grants_guest_redaction_and_session_revocation(hub, monkeypatch):
    settings, db, _ = hub
    cli.initialize(settings, db)
    application = app.create_app(settings)
    with TestClient(application) as admin, closing(TestClient(application)) as guest:
        assert admin.get(API + "/hosts").status_code == 401
        assert admin.post(API + "/login", json=ADMIN).status_code == 403
        original_token = login(admin)
        host_id = get(admin, "/hosts")[0]["id"]
        wait_for_status(admin, host_id, "online")
        credentials = {"username": "visitor", "password": "guest-password-123"}
        created = admin.post(API + "/admin/users", json=credentials | {"role": "guest"}, headers=CSRF)
        assert created.status_code == 201
        assert created.json()["host_ids"] == []
        login(guest, credentials)
        resource = f"/hosts/{host_id}"
        assert get(guest, "/hosts") == []
        for suffix in ("", "/metrics", "/history"):
            assert guest.get(API + resource + suffix).status_code == 404
        assert guest.get(API + "/admin/users").status_code == 403
        grant = API + f"/admin/users/{created.json()['id']}/hosts/{host_id}"
        assert admin.put(grant).status_code == 403
        assert admin.put(grant, headers=CSRF).status_code == 204
        assert get(guest, resource)["observed_hostname"] is None
        metrics = guest.get(API + resource + "/metrics")
        assert metrics.headers["cache-control"] == "no-store"
        assert "collectors" not in metrics.json()
        assert "eth0" not in metrics.text
        assert "192.0.2.8" not in metrics.text
        assert metrics.json()["summary"]["download_bytes_per_second"] == 1048576
        assert "eth0" not in guest.get(API + resource + "/history").text
        assert admin.delete(grant, headers=CSRF).status_code == 204
        assert guest.get(API + resource + "/history").status_code == 404
        guest_token = guest.cookies[COOKIE]
        assert guest.post(API + "/logout", headers=CSRF).status_code == 204
        guest.cookies.set(COOKIE, guest_token)
        assert guest.get(API + "/me").status_code == 401

        new_password = "replacement-admin-password"
        monkeypatch.setattr(cli.getpass, "getpass", lambda prompt: new_password)
        cli.reset_password(db, ADMIN["username"])
        assert admin.cookies[COOKIE] == original_token
        assert admin.get(API + "/me").status_code == 401
        assert admin.post(API + "/login", json=ADMIN, headers=CSRF).status_code == 401
        login(admin, ADMIN | {"password": new_password})


def test_history_deduplicates_samples_and_retains_hourly_averages(hub):
    settings, db, agent = hub
    cli.initialize(settings, db)
    with db.connect() as connection:
        host_id = connection.execute("SELECT id FROM hosts").fetchone()[0]
    hour = int(time.time() // 3600) * 3600
    now = hour + 1800
    for offset, value in ((10, 10), (10, 10), (30, None), (40, 20)):
        agent.sampled_at, agent.cpu = hour + offset, value
        record_snapshot(db, host_id, agent.snapshot(), now)
    with db.connect(write=True) as connection:
        samples = history(connection, host_id, 6, now)["series"]["cpu_percent"]
        assert [value for _, value in samples] == [10, None, 20]
        prune_history(connection, now + 8 * DAY)
        assert not connection.execute("SELECT 1 FROM metric_samples").fetchone()
        hourly = history(connection, host_id, 2160, now + 8 * DAY)
        assert hourly["series"]["cpu_percent"] == [[timestamp(hour), 15.0]]
        prune_history(connection, now + 91 * DAY)
        assert not connection.execute("SELECT 1 FROM metric_hourly").fetchone()
