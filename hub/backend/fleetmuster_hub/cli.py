import argparse
import asyncio
import getpass
import sqlite3
import sys
from uuid import uuid4

import httpx
import uvicorn
from pydantic import ValidationError

from .auth import NewUser, passwords
from .config import Settings
from .db import Database, audit
from .polling import agent_client


async def check_agent(settings):
    try:
        async with agent_client(settings) as client:
            response = await client.get("/health")
            response.raise_for_status()
            if response.json() != {"status": "ok"}:
                raise ValueError("Unexpected health response")
    except (httpx.HTTPError, ValueError) as exc:
        raise RuntimeError(
            f"Start the native fleetmuster agent and check {settings.agent_url}/health"
        ) from exc


def initialized(db):
    if not db.path.exists():
        return False
    with db.connect() as connection:
        if not connection.execute("PRAGMA user_version").fetchone()[0]:
            return False
        return bool(connection.execute("SELECT 1 FROM users WHERE role = 'admin'").fetchone())


def ask_password():
    password = getpass.getpass("Password: ")
    if password != getpass.getpass("Confirm password: "):
        raise RuntimeError("Passwords do not match")
    if not 12 <= len(password) <= 1024:
        raise RuntimeError("Use between 12 and 1024 characters for the password")
    return password


def initialize(settings, db):
    if initialized(db):
        print("Hub is already initialized.")
        return
    asyncio.run(check_agent(settings))
    username = input("Admin username: ").strip()
    user = NewUser(username=username, password=ask_password(), role="admin")
    hashed = passwords.hash(user.password)
    db.migrate()
    with db.connect(write=True) as connection:
        if connection.execute("SELECT 1 FROM users WHERE role = 'admin'").fetchone():
            print("Hub is already initialized.")
            return
        user_id = connection.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'admin')",
            (user.username, hashed),
        ).lastrowid
        connection.execute(
            "INSERT OR IGNORE INTO hosts (id, name, kind) VALUES (?, 'localhost', 'local')",
            (str(uuid4()),),
        )
        connection.execute(
            "INSERT INTO host_access SELECT ?, id FROM hosts WHERE kind = 'local'", (user_id,),
        )
        audit(connection, "initialize", user_id)
    print("Hub initialized.")


def reset_password(db, username):
    if not initialized(db):
        raise RuntimeError("Run fleetmuster-hub init first")
    with db.connect() as connection:
        user = connection.execute(
            "SELECT id FROM users WHERE username = ? AND role = 'admin'", (username,),
        ).fetchone()
    if user is None:
        raise RuntimeError("Admin account not found")
    hashed = passwords.hash(ask_password())
    with db.connect(write=True) as connection:
        connection.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hashed, user["id"]))
        connection.execute("DELETE FROM sessions WHERE user_id = ?", (user["id"],))
        audit(connection, "reset_password", subject=username)
    print("Password reset. Existing sessions were revoked.")


def main():
    parser = argparse.ArgumentParser(prog="fleetmuster-hub")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="Set up a local host and initial admin")
    commands.add_parser("serve", help="Run the hub")
    reset = commands.add_parser("reset-password", help="Reset a local admin password")
    reset.add_argument("username")
    args = parser.parse_args()
    try:
        settings = Settings.from_env()
        db = Database(settings.data_dir)
        if args.command == "init":
            initialize(settings, db)
        elif args.command == "reset-password":
            reset_password(db, args.username)
        else:
            if not initialized(db):
                raise RuntimeError("Run fleetmuster-hub init first")
            if settings.frontend_dir is None or not (settings.frontend_dir / "index.html").is_file():
                raise RuntimeError("Build the frontend or set FLEETMUSTER_FRONTEND_DIR to its build directory")
            from .app import create_app

            uvicorn.run(
                create_app(settings), host=settings.bind, port=settings.port, workers=1,
                proxy_headers=True, forwarded_allow_ips="127.0.0.1,::1",
            )
    except ValidationError as exc:
        for error in exc.errors(include_input=False, include_context=False):
            print(error["msg"], file=sys.stderr)
        return 1
    except (ValueError, RuntimeError, OSError, sqlite3.Error, EOFError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0
