# fleetmuster - standalone hub

> [!NOTE]
> this document is meant for AI agents to implement the plan.

## Goal

Build a usable single machine installation: the existing agent and a separate fastapi hub on the same computer, with a React frontend. Design the hub so remote SSH hosts can be added later, but for now, the hub will only manage the local agent. make sure that later, we do not have to completely rewrite the host model or frontend to support remote hosts.

inspect the existing agent code and identify the parts that need to be modified to support the hub. make sure that the agent is separate. the browser only talks to the hub, and the hub talks to the agent. The agent should be able to run without the hub. standalone installation requires the local agent, but if it goes offline later, the hub should keep working and show its last known state.

the hub should work both natively and in Docker on Linux. the agent must always run natively on the host, not inside the hub container. do not make two separate hub implementations.

## done when...

- a fresh install can create an admin, login, and display its own host (named localhost) in the frontend, automatically
- restarting the hub persists users, metric history, identity, and other things that need to be persisted.
- users cannot access hosts they are not granted access to.
- browser requests read hub's cache, not the agent directly. when polling fails, the api does not break
- missing values are not displayed as 0, and the frontend shows when data is stale or unavailable.
- the hub works both natively and through Docker Compose on Linux, while the agent runs natively.
- rebuilding or replacing the Docker container does not lose the database, users, secrets, or other persistent data.
- the Docker image works on both ARM64 and x86-64 Linux machines.
- tests covering useful stuff. do not make your tests slop. the global AGENT.md should have instructions on what to avoid.

## Suggestions

These are made by another LLM, and are not necessarily the best way to implement the hub. They are meant to be a starting point, or for you to discuss with me, with the `question` tool. Treat these as suggestions, not requirements. You may find better ways to implement the hub.

### Implementation order

1. Backend foundation: Create `hub/backend/` with its own `pyproject.toml`, FastAPI app, configuration, and SQLite database. Use SQLAlchemy and Alembic migrations. Store the database outside the repository; enable WAL. Run one hub worker to avoid duplicate pollers.
2. Local host: On startup, idempotently create exactly one host with `kind=local` and a stable UUID. Preserve its display name, ID, permissions, and history across restarts. Its observed hostname comes from agent metrics, not the hub's own hostname (important for containers).
3. Authentication: Add local users with Admin, Operator, Viewer, and Guest roles. Create the first admin through a password-prompting CLI, never a default password or public setup endpoint. Use Argon2id password hashes, revocable server-side sessions, HttpOnly cookies, CSRF protection, and login throttling. Admins grant users access to specific hosts. Enforce roles and host grants in backend routes; Guests receive metrics/history only, with sensitive host/network details removed.
4. Polling and history: Start a background hub poller, never collect metrics inside browser request handlers. Poll the local agent roughly every 60 seconds when idle and every 10 seconds for an actively viewed host. Cache the latest snapshot and store samples in SQLite using bounded batch writes. Keep 7 days of detailed data and 90 days of hourly aggregates. Preserve per-collector freshness. If the agent is unavailable, show last contact and stale data, retry with exponential backoff capped at 5 minutes and jitter. No notifications or automatic repair.
5. Hub API and frontend: Implement authenticated `GET /api/v1/hosts`, `GET /api/v1/hosts/{id}`, `GET /api/v1/hosts/{id}/metrics`, and `GET /api/v1/hosts/{id}/history`, plus login/logout/me and minimal admin user/grant endpoints. Build `hub/frontend/` with React, TypeScript, and Vite. Include login, host list, host details, current CPU/RAM/swap/disk/network/temperature/system values, recent charts, and stale/unavailable states. Display MiB/s from the agent's bytes-per-second rates.
6. Live activity: The agent's `set_active()` currently works only within its own process. Add a narrowly scoped, authenticated loopback control with a short expiry so hub activity can request faster sampling without leaving it on permanently. Keep the agent bound to `127.0.0.1`, and make the hub's agent URL and other deployment settings configurable.
7. Deployment: Add native startup instructions and a production Dockerfile and Compose configuration for the hub. Build the React frontend and FastAPI backend into one image, served from the same origin. Do not put the agent in the image.

### Dockerisation

- use Linux host networking for the standalone hub so it can reach the native agent at `127.0.0.1:7070`. do not expose the agent on `0.0.0.0` just to make Docker work. do not add a `ports` mapping when using host networking.
- keep the hub's listening address and port configurable. bind to localhost by default. if users want to access it over a network, document how to put it behind HTTPS.
- run one hub worker as a non-root user. don't mount the Docker socket or run the container privileged.
- persist SQLite, its WAL files, secrets, and other hub data in a volume. migrations and container upgrades must preserve that data. make sure volume permissions work for the non-root user.
- support Linux ARM64 and AMD64. add a `.dockerignore` and a health check. no need to support Docker Desktop for now.
- keep any secret used for the agent's active-sampling control outside the repo. setup should make it available to the native agent and hub without making the user copy it manually. mount it read-only in Docker.
- native and Docker installs should use the same init command and application code. don't create a separate setup system for Docker.

### First install

1. install and start the agent natively. check that its `/health` endpoint responds on `127.0.0.1:7070`. if it doesn't, the hub init command should say what's wrong instead of continuing with a broken standalone install.
2. choose native or Docker for the hub. both should use the same configuration options and persistent data layout.
3. run an init command, for example `fleetmuster-hub init`. it should create the data directory, run database migrations, generate and save secrets, and prompt for an admin username and password. don't use default credentials or an unauthenticated web setup page. running init again must not overwrite existing data or create another initial admin.
4. for Docker, the same command should work before starting the service, for example `docker compose run --rm hub fleetmuster-hub init`. then start the hub with `docker compose up -d`.
5. start the hub. it should register `localhost` once, with a persistent UUID and access granted to the first admin. take the observed hostname from the agent, not the container. log in and show the host and whatever metrics are available.
6. if the agent goes offline after setup, keep the hub running. show stale data and last contact, and retry automatically. don't send alerts or try to repair the machine.

provide a local CLI for resetting an admin password. don't add an unauthenticated web recovery endpoint. test fresh installs, repeated init, restarting the hub, the agent going offline, Docker container recreation, and persistence across restarts.

### Minimum database tables

`users`, `sessions`, `hosts`, `host_access`, `metric_samples`, `metric_hourly`, `audit_events`. Use foreign keys, unique constraints, migrations, and immediate commits for authentication, access changes, and audit events.

---

**Out of Scope** (for now): SSH onboarding, remote terminal, remote commands, reboot/shutdown, system updates, alerts, cloud services.

keep your code readable, and avoid premature optimisation. Use the `question` tool to ask me for clarification or suggestions. When in doubt, ask me instead of guessing or comtemplating for ages.

**Do NOT commit or push any code until you have a working prototype that meets the above requirements.**
