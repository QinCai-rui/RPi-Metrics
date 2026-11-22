# fleetmuster standalone hub

Run the native agent and the hub on the same Linux machine. Open the dashboard at
http://127.0.0.1:8080. The dashboard reads the hub's saved metrics. If the agent
stops, the hub keeps the last readings, marks them stale, and retries.

For faster sampling while the dashboard is visible, set the same
`FLEETMUSTER_ACTIVITY_TOKEN` in the agent and hub environments before starting
them. Generate a value with `openssl rand -hex 32`. Use a private shell
environment or a gitignored environment file. Compose reads the token from its
environment, so export it before running `docker compose up -d`.

## Start the native agent

From the repository root, start the agent and leave it running.

```sh
uv run --no-project --with-requirements agent/requirements.txt \
  python -m uvicorn agent.main:app --host 127.0.0.1 --port 7070
```

In another terminal, check that the agent is ready.

```sh
curl --fail http://127.0.0.1:7070/health
```

## Run the hub natively

Install [uv](https://docs.astral.sh/uv/) and [Bun](https://bun.sh/). From the
repository root, build the dashboard, then initialize the hub.

```sh
cd hub/frontend
bun install --frozen-lockfile
bun run --bun build
cd ../backend
uv sync --locked --no-dev
uv run --no-dev fleetmuster-hub init
uv run --no-dev fleetmuster-hub serve
```

Enter a username and password when prompted. Use at least 12 characters for the
password. Sign in at http://127.0.0.1:8080. The hub adds `localhost` to the first
admin's host list. If you run `init` again, it keeps the existing account and host.

## Run the hub in Docker

Use Docker Engine and Docker Compose on Linux. Keep the native agent running.
From the repository root, run these commands.

```sh
cd hub
docker compose build
docker compose run --rm hub fleetmuster-hub init
docker compose up -d
```

Sign in at http://127.0.0.1:8080. The container uses Linux host networking to reach
the agent over loopback. The same Dockerfile builds for Linux AMD64 and ARM64.

To replace the container after an update, run `docker compose up -d --build`
from the same directory. Keep the Compose project name and the `hub-data`
volume. The hub stores the database and its WAL files in that volume. Removing
the volume with `docker compose down -v` deletes users, sessions, and metrics.

## Grant access or reset an admin password

As an admin, open **Manage users**, create a user, and select the hosts they can
see under **Host access**. An admin account also needs a host grant to read that
host's metrics. Operators and viewers have read access to their assigned hosts.
Guests can read aggregate metrics and history, with host identifiers such as
the observed hostname and network interface names omitted.

Reset an admin password from the machine running the hub. This signs the
account out of all browsers. Use the same data directory or Compose project name
you used during setup.

```sh
# Native, from hub/backend
uv run --no-dev fleetmuster-hub reset-password USERNAME

# Docker, from hub
docker compose run --rm hub fleetmuster-hub reset-password USERNAME
```

## Settings

| Environment variable | Default | Purpose |
| --- | --- | --- |
| `FLEETMUSTER_AGENT_URL` | `http://127.0.0.1:7070` | Native agent HTTP loopback origin |
| `FLEETMUSTER_BIND` | `127.0.0.1` | Hub listening address |
| `FLEETMUSTER_PORT` | `8080` | Hub listening port |
| `FLEETMUSTER_SECURE_COOKIE` | `0` | Set to `1` for HTTPS |
| `FLEETMUSTER_ACTIVITY_TOKEN` | Unset | Shared token for faster sampling while viewing a host |
| `FLEETMUSTER_DATA_DIR` | `$XDG_DATA_HOME/fleetmuster` or `~/.local/share/fleetmuster` | Native database directory. Docker uses `/data`. |
| `FLEETMUSTER_FRONTEND_DIR` | `hub/frontend/dist` for an editable native install | Directory containing the built dashboard. Docker uses `/app/frontend`. |

For network access, keep the hub bound to `127.0.0.1` and run an HTTPS reverse
proxy on the same machine. Forward all paths to `http://127.0.0.1:8080` and
overwrite `X-Forwarded-For` with the client's address. Set
`FLEETMUSTER_SECURE_COOKIE=1` for the hub and use the HTTPS address to sign in.
Keep the agent on loopback.

The hub polls every 60 seconds while idle and every 2 seconds while a visible
browser tab views the host. With the shared token, the agent samples CPU, memory,
and network every 5 seconds, disk and temperature every 10 seconds, and system
information every 30 seconds while the host is being viewed. The agent goes back
to its idle intervals within about 20 seconds after the last tab stops viewing the
host. The hub keeps recorded samples for 7 days and hourly averages for 90 days.
Network totals exclude loopback and virtual interfaces. The collector details
show rates for individual non-loopback interfaces.

## Run the tests

Run these commands from the repository root.

```sh
uv run --project hub/backend --locked pytest hub/backend/tests
uv run --no-project --with-requirements agent/requirements.txt --with pytest python -m pytest agent/tests
```
