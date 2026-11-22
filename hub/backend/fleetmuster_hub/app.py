import asyncio
import secrets
import sqlite3
import time
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.staticfiles import StaticFiles

from .auth import (
    COOKIE,
    SESSION_SECONDS,
    Credentials,
    LoginThrottle,
    NewUser,
    current_user,
    digest,
    dummy_hash,
    passwords,
    require_csrf,
    verify_password,
)
from .config import Settings
from .db import Database, audit
from .metrics import cached_metrics, history, host_info
from .polling import Poller

api = APIRouter(prefix="/api/v1")
User = Annotated[dict, Depends(current_user)]
Mutation = Depends(require_csrf)


def require_admin(user: User):
    if user["role"] != "admin":
        raise HTTPException(403, "Admin access required")
    return user


Admin = Annotated[dict, Depends(require_admin)]


def granted_host(connection, host_id, user):
    host = connection.execute(
        """SELECT hosts.* FROM hosts JOIN host_access ON hosts.id = host_id
        WHERE hosts.id = ? AND user_id = ?""", (host_id, user["id"]),
    ).fetchone()
    if host is None:
        raise HTTPException(404, "Host not found")
    return host


@api.post("/login", dependencies=[Mutation])
def login(request: Request, response: Response, credentials: Credentials):
    request.app.state.throttle.check(request.client.host if request.client else "unknown")
    db = request.app.state.db
    with db.connect() as connection:
        user = connection.execute("SELECT * FROM users WHERE username = ?", (credentials.username,)).fetchone()
    valid = verify_password(credentials.password, user["password_hash"] if user else dummy_hash)
    if not valid or user is None:
        raise HTTPException(401, "Username or password is incorrect")

    token = secrets.token_urlsafe(32)
    now = int(time.time())
    with db.connect(write=True) as connection:
        current_hash = connection.execute("SELECT password_hash FROM users WHERE id = ?", (user["id"],)).fetchone()
        if not current_hash or current_hash[0] != user["password_hash"]:
            raise HTTPException(401, "Username or password is incorrect")
        connection.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))
        old_token = request.cookies.get(COOKIE)
        if old_token:
            connection.execute("DELETE FROM sessions WHERE token_hash = ?", (digest(old_token),))
        connection.execute("INSERT INTO sessions VALUES (?, ?, ?)",
                           (digest(token), user["id"], now + SESSION_SECONDS))
        audit(connection, "login", user["id"])

    response.set_cookie(COOKIE, token, max_age=SESSION_SECONDS, httponly=True, samesite="strict",
                        secure=request.app.state.settings.secure_cookie)
    return {key: user[key] for key in ("id", "username", "role")}


@api.post("/logout", dependencies=[Mutation], status_code=204)
def logout(request: Request, response: Response, user: User):
    with request.app.state.db.connect(write=True) as connection:
        connection.execute("DELETE FROM sessions WHERE token_hash = ?", (digest(request.cookies[COOKIE]),))
        audit(connection, "logout", user["id"])
    response.delete_cookie(COOKIE)


@api.get("/me")
def me(user: User):
    return user


@api.get("/hosts")
def hosts(request: Request, user: User):
    with request.app.state.db.connect() as connection:
        rows = connection.execute(
            """SELECT id, name, kind, observed_hostname, last_contact, online
            FROM hosts JOIN host_access ON hosts.id = host_id
            WHERE user_id = ? ORDER BY name""", (user["id"],),
        )
        return [host_info(host, user["role"], request.app.state.settings.idle_poll) for host in rows]


@api.get("/hosts/{host_id}")
def detail(request: Request, host_id: str, user: User):
    with request.app.state.db.connect() as connection:
        host = granted_host(connection, host_id, user)
    return host_info(host, user["role"], request.app.state.settings.idle_poll)


@api.get("/hosts/{host_id}/metrics")
def metrics(request: Request, host_id: str, user: User):
    with request.app.state.db.connect() as connection:
        host = granted_host(connection, host_id, user)
    request.app.state.poller.view(host_id)
    interval = request.app.state.settings.idle_poll
    return cached_metrics(host, host_info(host, user["role"], interval), user["role"], interval)


@api.get("/hosts/{host_id}/history")
def host_history(request: Request, host_id: str, user: User, hours: int = Query(6, ge=1, le=2160)):
    with request.app.state.db.connect() as connection:
        granted_host(connection, host_id, user)
        return history(connection, host_id, hours, time.time())


@api.get("/admin/users")
def list_users(request: Request, admin: Admin):
    with request.app.state.db.connect() as connection:
        users = [dict(row) | {"host_ids": []} for row in connection.execute(
            "SELECT id, username, role FROM users ORDER BY username"
        )]
        by_id = {user["id"]: user for user in users}
        for row in connection.execute("SELECT user_id, host_id FROM host_access"):
            by_id[row["user_id"]]["host_ids"].append(row["host_id"])
        hosts = [dict(row) for row in connection.execute("SELECT id, name FROM hosts ORDER BY name")]
    return {"users": users, "hosts": hosts}


@api.post("/admin/users", dependencies=[Mutation], status_code=201)
def create_user(request: Request, admin: Admin, new_user: NewUser):
    hashed = passwords.hash(new_user.password)
    with request.app.state.db.connect(write=True) as connection:
        try:
            user_id = connection.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                (new_user.username, hashed, new_user.role),
            ).lastrowid
        except sqlite3.IntegrityError as exc:
            raise HTTPException(409, "Username is already in use") from exc
        audit(connection, "create_user", admin["id"], str(user_id))
    return {"id": user_id, "username": new_user.username, "role": new_user.role, "host_ids": []}


@api.put("/admin/users/{user_id}/hosts/{host_id}", dependencies=[Mutation], status_code=204)
@api.delete("/admin/users/{user_id}/hosts/{host_id}", dependencies=[Mutation], status_code=204)
def change_grant(request: Request, admin: Admin, user_id: int, host_id: str):
    grant = request.method == "PUT"
    with request.app.state.db.connect(write=True) as connection:
        user = connection.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone()
        host = connection.execute("SELECT 1 FROM hosts WHERE id = ?", (host_id,)).fetchone()
        if not user or not host:
            raise HTTPException(404, "User or host not found")
        statement = ("INSERT OR IGNORE INTO host_access (user_id, host_id) VALUES (?, ?)" if grant else
                     "DELETE FROM host_access WHERE user_id = ? AND host_id = ?")
        if connection.execute(statement, (user_id, host_id)).rowcount:
            audit(connection, "grant_host" if grant else "revoke_host", admin["id"], f"{user_id}/{host_id}")


def create_app(settings=None):
    settings = settings or Settings.from_env()
    db = Database(settings.data_dir)

    @asynccontextmanager
    async def lifespan(app):
        if not db.path.exists():
            raise RuntimeError("Run fleetmuster-hub init first")
        db.migrate()
        with db.connect() as connection:
            host = connection.execute("SELECT id FROM hosts WHERE kind = 'local'").fetchone()
            admin = connection.execute("SELECT 1 FROM users WHERE role = 'admin'").fetchone()
        if not host or not admin:
            raise RuntimeError("Run fleetmuster-hub init first")
        poller = app.state.poller = Poller(settings, db, host["id"])
        task = asyncio.create_task(poller.run())
        try:
            yield
        finally:
            poller.stop.set()
            poller.wake.set()
            await task

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None, redirect_slashes=False)
    app.state.settings = settings
    app.state.db = db
    app.state.throttle = LoginThrottle()

    @app.middleware("http")
    async def no_api_cache(request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/health")
    def health():
        return {"status": "ok"}

    app.include_router(api)
    if settings.frontend_dir and (settings.frontend_dir / "index.html").is_file():
        app.mount("/", StaticFiles(directory=settings.frontend_dir, html=True))
    return app
