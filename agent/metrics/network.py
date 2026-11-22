
import socket
from pathlib import Path

import psutil


def classify_interface(name):
    if name == "lo":
        return "loopback"

    path = Path("/sys/class/net") / name

    try:
        if not path.exists():
            return "unknown"

        if path.resolve().is_relative_to("/sys/devices/virtual/net"):
            return "virtual"

        return "physical"
    except OSError:
        return "unknown"


def collect_network():
    counters = psutil.net_io_counters(pernic=True)
    stats = psutil.net_if_stats()
    addresses = psutil.net_if_addrs()

    interfaces = {}

    for name, io in counters.items():
        info = stats.get(name)
        addrs = addresses.get(name, [])

        interfaces[name] = {
            "type": classify_interface(name),
            "is_up": info.isup if info else None,
            "mtu_bytes": info.mtu if info else None,
            "link_speed_mbps": info.speed if info and info.speed > 0 else None,
            "mac_address": next(
                (addr.address for addr in addrs if addr.family == psutil.AF_LINK),
                None,
            ),
            "ipv4_addresses": [
                addr.address for addr in addrs if addr.family == socket.AF_INET
            ],
            "ipv6_addresses": [
                addr.address for addr in addrs if addr.family == socket.AF_INET6
            ],
            "bytes_sent": io.bytes_sent,
            "bytes_received": io.bytes_recv,
            "packets_sent": io.packets_sent,
            "packets_received": io.packets_recv,
            "errors_in": io.errin,
            "errors_out": io.errout,
            "drops_in": io.dropin,
            "drops_out": io.dropout,
        }

    return {"interfaces": interfaces}
