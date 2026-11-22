
import psutil


def collect_disk():
    filesystems = []

    for partition in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(partition.mountpoint)
        except OSError:
            continue

        filesystems.append({
            "device": partition.device,
            "mountpoint": partition.mountpoint,
            "filesystem": partition.fstype,
            "mount_options": partition.opts,
            "total_bytes": usage.total,
            "used_bytes": usage.used,
            "free_bytes": usage.free,
            "usage_percent": usage.percent,
        })

    io = psutil.disk_io_counters(perdisk=True, nowrap=False)

    return {
        "filesystems": filesystems,
        "io": {
            device: {
                "read_bytes": stats.read_bytes,
                "write_bytes": stats.write_bytes,
                "read_time_ms": stats.read_time,
                "write_time_ms": stats.write_time,
                "read_count": stats.read_count,
                "write_count": stats.write_count,
            }
            for device, stats in io.items()
        } if io else None,
    }
