import os
import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path

# Each tuple is one migration, applied in a transaction with its version bump.
MIGRATIONS = (
    (
        """CREATE TABLE users (
            id INTEGER PRIMARY KEY, username TEXT NOT NULL COLLATE NOCASE UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('admin', 'operator', 'viewer', 'guest'))
        )""",
        """CREATE TABLE sessions (
            token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            expires_at INTEGER NOT NULL
        )""",
        """CREATE TABLE hosts (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL,
            observed_hostname TEXT, last_contact REAL, online INTEGER NOT NULL DEFAULT 0,
            snapshot TEXT
        )""",
        "CREATE UNIQUE INDEX one_local_host ON hosts(kind) WHERE kind = 'local'",
        """CREATE TABLE host_access (
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            host_id TEXT NOT NULL REFERENCES hosts(id) ON DELETE CASCADE,
            PRIMARY KEY (user_id, host_id)
        )""",
        """CREATE TABLE metric_samples (
            host_id TEXT NOT NULL REFERENCES hosts(id) ON DELETE CASCADE,
            collector TEXT NOT NULL, sampled_at REAL NOT NULL, values_json TEXT NOT NULL,
            PRIMARY KEY (host_id, collector, sampled_at)
        )""",
        "CREATE INDEX metric_samples_time ON metric_samples(host_id, sampled_at)",
        """CREATE TABLE metric_hourly (
            host_id TEXT NOT NULL REFERENCES hosts(id) ON DELETE CASCADE,
            metric TEXT NOT NULL, hour INTEGER NOT NULL, total REAL NOT NULL, count INTEGER NOT NULL,
            PRIMARY KEY (host_id, hour, metric)
        )""",
        """CREATE TABLE audit_events (
            id INTEGER PRIMARY KEY, happened_at INTEGER NOT NULL DEFAULT (CAST(strftime('%s', 'now') AS INTEGER)),
            actor_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            action TEXT NOT NULL, subject TEXT
        )""",
    ),
)


class Database:
    def __init__(self, directory: Path):
        self.path = directory / "hub.sqlite3"

    @contextmanager
    def connect(self, *, write=False):
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            with connection:
                yield connection
        finally:
            connection.close()

    def migrate(self):
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.close(os.open(self.path, os.O_CREAT | os.O_RDONLY, 0o600))
        with closing(sqlite3.connect(self.path, timeout=5)) as connection:
            connection.execute("PRAGMA journal_mode = WAL")
        with self.connect(write=True) as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version > len(MIGRATIONS):
                raise RuntimeError("The database was created by a newer hub")
            for statements in MIGRATIONS[version:]:
                for statement in statements:
                    connection.execute(statement)
            connection.execute(f"PRAGMA user_version = {len(MIGRATIONS)}")


def audit(connection, action, actor_id=None, subject=None):
    connection.execute(
        "INSERT INTO audit_events (action, actor_id, subject) VALUES (?, ?, ?)",
        (action, actor_id, subject),
    )
