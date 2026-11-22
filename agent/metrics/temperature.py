import psutil


def collect_temperature():
    try:
        sensors = psutil.sensors_temperatures()
    except (AttributeError, OSError, NotImplementedError):
        return None
    if not sensors:
        return None
    return {
        name: [{"label": item.label, "current_celsius": item.current,
                "high_celsius": item.high, "critical_celsius": item.critical}
               for item in readings]
        for name, readings in sensors.items()
    }
