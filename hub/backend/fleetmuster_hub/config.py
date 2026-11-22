import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    agent_url: str = "http://127.0.0.1:7070"
    bind: str = "127.0.0.1"
    port: int = 8080
    secure_cookie: bool = False
    frontend_dir: Path | None = None
    idle_poll: float = 60
    active_poll: float = 2
    activity_token: str = field(default="", repr=False)

    @classmethod
    def from_env(cls):
        data_home = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
        frontend = Path(__file__).resolve().parents[2] / "frontend/dist"
        return cls(
            data_dir=Path(os.environ.get("FLEETMUSTER_DATA_DIR", data_home / "fleetmuster")),
            agent_url=os.environ.get("FLEETMUSTER_AGENT_URL", "http://127.0.0.1:7070"),
            bind=os.environ.get("FLEETMUSTER_BIND", "127.0.0.1"),
            port=int(os.environ.get("FLEETMUSTER_PORT", "8080")),
            secure_cookie=os.environ.get("FLEETMUSTER_SECURE_COOKIE") == "1",
            frontend_dir=Path(os.environ.get("FLEETMUSTER_FRONTEND_DIR", frontend)),
            activity_token=os.environ.get("FLEETMUSTER_ACTIVITY_TOKEN", ""),
        )

    def __post_init__(self):
        url = urlsplit(self.agent_url)
        if (url.scheme != "http" or url.hostname not in {"127.0.0.1", "::1", "localhost"}
                or url.username is not None or url.path not in {"", "/"}
                or url.query or url.fragment):
            raise ValueError("FLEETMUSTER_AGENT_URL must be an HTTP loopback origin")
        if not 0 < self.active_poll <= self.idle_poll:
            raise ValueError("Polling intervals must be positive and active must be at most idle")
