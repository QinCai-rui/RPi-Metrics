import hashlib
import re
import secrets
import threading
import time
from typing import Literal

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import HTTPException, Request
from pydantic import BaseModel, Field, field_validator

COOKIE = "fleetmuster_session"
SESSION_SECONDS = 7 * 86400
Role = Literal["admin", "operator", "viewer", "guest"]
passwords = PasswordHasher()
dummy_hash = passwords.hash(secrets.token_urlsafe())


class Credentials(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=1024)


class NewUser(Credentials):
    role: Role

    @field_validator("username")
    @classmethod
    def check_username(cls, value):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", value):
            raise ValueError("Use letters, digits, dots, underscores, or hyphens")
        return value

    @field_validator("password")
    @classmethod
    def check_password(cls, value):
        if len(value) < 12:
            raise ValueError("Use at least 12 characters for the password")
        return value


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def verify_password(password, hashed):
    try:
        passwords.verify(hashed, password)
    except VerifyMismatchError:
        return False
    return True


def require_csrf(request: Request):
    # A cross-origin browser cannot send this custom header without CORS permission.
    if request.headers.get("X-Fleetmuster-Request") != "1":
        raise HTTPException(403, "Missing request header")


def current_user(request: Request):
    token = request.cookies.get(COOKIE)
    if token and len(token) == 43:
        with request.app.state.db.connect() as connection:
            user = connection.execute(
                """SELECT users.id, username, role FROM users JOIN sessions ON user_id = users.id
                WHERE token_hash = ? AND expires_at > ?""",
                (digest(token), time.time()),
            ).fetchone()
        if user:
            return dict(user)
    raise HTTPException(401, "Sign in to continue")


class LoginThrottle:
    def __init__(self):
        self.lock = threading.Lock()
        self.window = 0
        self.attempts = {}

    def check(self, address):
        window = int(time.monotonic() // 60)
        with self.lock:
            if window != self.window:
                self.window = window
                self.attempts.clear()
            if len(self.attempts) >= 1024 and address not in self.attempts:
                address = "other"
            attempts = self.attempts.get(address, 0)
            if attempts >= 10:
                raise HTTPException(429, "Too many sign-in attempts. Try again in a minute.")
            self.attempts[address] = attempts + 1
