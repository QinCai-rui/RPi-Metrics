import platform
import socket
import time
from datetime import datetime, timezone

import psutil

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
        "boot_time": datetime.fromtimestamp(
            boot_time, timezone.utc
        ).isoformat(),
        "uptime_seconds": int(time.time() - boot_time),
    }
