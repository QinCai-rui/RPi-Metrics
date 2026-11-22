import platform
import socket
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import psutil


PLATFORM_PROFILE = Path("/sys/firmware/acpi/platform_profile")


def _command(*args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=1, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def detect_power_profile():
    # Successful queries indicate that the respective service is running.
    profile = _command("powerprofilesctl", "get")
    if profile and "\n" not in profile:
        return {"name": profile, "source": "powerprofilesctl"}
    output = _command("tuned-adm", "active")
    prefix = "Current active profile:"
    if output and output.startswith(prefix):
        profile = output[len(prefix):].strip()
        if profile:
            return {"name": profile, "source": "tuned"}
    try:
        profile = PLATFORM_PROFILE.read_text().strip()
    except (OSError, UnicodeError):
        profile = None
    return {"name": profile, "source": "platform_profile"} if profile else None


def collect_system():
    try:
        distro = platform.freedesktop_os_release()
    except OSError:
        distro = {}
    boot_time = psutil.boot_time()
    return {
        "hostname": socket.gethostname(),
        "os": platform.system(),
        "distribution": distro.get("PRETTY_NAME"),
        "distribution_id": distro.get("ID"),
        "distribution_version": distro.get("VERSION_ID"),
        "architecture": platform.machine(),
        "kernel": platform.release(),
        "boot_time": datetime.fromtimestamp(boot_time, timezone.utc).isoformat(),
        "uptime_seconds": int(time.time() - boot_time),
        "power_profile": detect_power_profile(),
    }
