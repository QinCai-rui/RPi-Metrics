import psutil

def collect_memory():
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()

    return {
        "ram": {
            "total_bytes": memory.total,
            "used_bytes": memory.used,
            "available_bytes": memory.available,
            "usage_percent": memory.percent,
        },
        "swap": {
            "total_bytes": swap.total,
            "used_bytes": swap.used,
            "free_bytes": swap.free,
            "usage_percent": swap.percent,
        },
    }
