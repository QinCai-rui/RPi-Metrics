# fleetmuster - standalone hub

> [!NOTE]
> this document is meant for AI agents to implement the plan.

## Goal

Build a usable single machine installation: the existing agent and a separate fastapi hub on the same computer, with a React frontend. Design the hub so remote SSH hosts can be added later, but for now, the hub will only manage the local agent. make sure that later, we do not have to completely rewrite the host model or frontend to support remote hosts.

inspect the existing agent code and identify the parts that need to be modified to support the hub. make sure that the agent is separate. the browser only talks to the hub, and the hub talks to the agent. The agent should be able to run without the hub, but standalone mode requires the local agent to be installed. If the agent temporarily becomes unavailable, the hub should remain operational and display its last known state.

Support both native and Docker installations for the hub. The agent must always run natively on the host, not inside the hub's container. Both installation methods should use the same backend, database, and frontend.

## done when...

- a fresh install can create an admin, login, and display its own host (named localhost) in the frontend, automatically
- restarting the hub persists users, metric history, identity, and other things that need to be persisted.
- users cannot access hosts they are not granted access to.
- browser requests read hub's cache, not the agent directly. when polling fails, the api does not break
- missing values are not displayed as 0, and the frontend shows when data is stale or unavailable.
- the hub works both natively and through Docker Compose on Linux, while the agent runs natively.
- rebuilding or replacing the Docker container does not lose database contents, user accounts, configuration, or other persistent data.
- the Docker installation works on both ARM64 and x86-64 Linux machines.
- tests covering useful stuff. do not make your tests slop. the global AGENT.md should have instructions on what to avoid.

## Suggestions

These are made by another LLM, and are not necessarily the best way to implement the hub. They are meant to be a starting point, or for you to discuss with me, with the `question` tool. Treat these as suggestions, not requirements. You may find better ways to implement the hub.

### Implementation order

1. Backend foundation: Create hub/backend/ with its own pyproject.toml, FastAPI app, configuration, and SQLite database. Use SQLAlchemy and Alembic migrations. Store the database outside the repository; enable WAL. Run one hub worker to avoid duplicate pollers.

2. Local host: On startup, idempotently create exactly one host with kind=local and a stable UUID. Preserve its display name, ID, permissions, and history across restarts. Its observed hostname comes from agent metrics, not the hub's own hostname (important for containers).

3. Authentication: Add local users with Admin, Operator, Viewer, and Guest roles. Create the first admin through a password-prompting CLI, never a default password or public setup endpoint. Use Argon2id password hashes, revocable server-side sessions, HttpOnly cookies, CSRF protection, and login throttling. Admins grant users access to specific hosts. Enforce roles and host grants in backend routes; Guests receive metrics/history only, with sensitive host/network details removed.

4. Polling and history: Start a background hub poller, never collect metrics inside browser request handlers. Poll the local agent roughly every 60 seconds when idle and every 10 seconds for an actively viewed host. Cache the latest snapshot and store samples in SQLite using bounded batch writes. Keep 7 days of detailed data and 90 days of hourly aggregates. Preserve per-collector freshness. If the agent is unavailable, show last contact and stale data, retry with exponential backoff capped at 5 minutes and jitter. No notifications or automatic repair.

5. Hub API and frontend: Implement authenticated GET /api/v1/hosts, GET /api/v1/hosts/{id}, GET /api/v1/hosts/{id}/metrics, and GET /api/v1/hosts/{id}/history, plus login/logout/me and minimal admin user/grant endpoints. Build hub/frontend/ with React, TypeScript, and Vite. Include login, host list, host details, current CPU/RAM/swap/disk/network/temperature/system values, recent charts, and stale/unavailable states. Display MiB/s from the agent's bytes-per-second rates.

6. Live activity and deployment: The agent's set_active() currently works only within its own process. Add a narrowly scoped, authenticated loopback control with a short expiry so hub activity can request faster sampling without leaving it on permanently. Document native startup first. Ensure the hub's agent URL, listening address, database location, and other deployment settings are configurable. Do not bind the agent to 0.0.0.0.

7. Dockerisation: Create a production Dockerfile for the hub and a Docker Compose configuration. Use a multi-stage build to compile the React frontend and package it with the FastAPI backend into a single image. The production frontend and API should use the same origin. Run the application as a non-root user, with one backend worker. Support Linux AMD64 and ARM64. Persist application data using a Docker volume, and make sure file ownership and permissions work correctly.

### Dockerisation requirements

- Use **Linux host networking** for the standalone hub container. This lets it access the native agent at `127.0.0.1:7070` without exposing the agent to the network. Ordinary Docker bridge networking cannot access a host service bound only to loopback.
- Do not use Docker's `ports` mapping together with host networking. Make the hub's listening address and port configurable so users can choose localhost-only access or LAN access.
- The Docker image must contain the hub only. Do not install or run the agent inside it.
- Do not require SSH to communicate with the local agent. Remote hosts will use SSH in a later stage.
- Use a persistent volume for SQLite, configuration, session secrets, and other persistent state. Database migrations must work across container upgrades.
- The initial admin creation CLI must also work inside the container using `docker compose exec`.
- Do not mount `/var/run/docker.sock`, use privileged containers, or grant unnecessary Linux capabilities.
- Do not hardcode passwords, tokens, or secrets in the Dockerfile or Compose configuration. If the hub needs a secret to authenticate to the local agent, use a secure configuration file or secret mounted into the container.
- Add a `.dockerignore`, a health check, and restart handling. Container startup must not create duplicate hosts or background pollers.
- Document the native installation and Docker Compose installation separately. Both must work without changes to application code.
- The Docker deployment is for Linux. Do not complicate the design to support Docker Desktop or other operating systems at this stage.

### Minimum database tables

users, sessions, hosts, host_access, metric_samples, metric_hourly, audit_events. Use foreign keys, unique constraints, migrations, and immediate commits for authentication, access changes, and audit events.

---

**Out of Scope** (for now): SSH onboarding, remote terminal, remote commands, reboot/shutdown, system updates, alerts, cloud services.

keep your code readable, and avoid premature optimisation. Use the `question` tool to ask me for clarification or suggestions. When in doubt, ask me instead of guessing or comtemplating for ages.

**Do NOT commit or push any code until you have a working prototype that meets the above requirements.**
