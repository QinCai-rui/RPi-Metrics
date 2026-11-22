from pathlib import Path

import psutil


CPU_SYSFS = Path("/sys/devices/system/cpu")


def scaling_governor(index):
    try:
        return (CPU_SYSFS / f"cpu{index}" / "cpufreq" / "scaling_governor").read_text().strip() or None
    except (OSError, UnicodeError):
        return None


class CPUCollector:
    """Calculate CPU usage from successive kernel CPU-time readings."""

    def __init__(self):
        self.previous_total = None
        self.previous_cores = None

    @staticmethod
    def _usage(previous, current):
        if previous is None or previous._fields != current._fields:
            return None
        delta = {name: getattr(current, name) - getattr(previous, name)
                 for name in current._fields}
        if any(value < 0 for value in delta.values()):
            return None
        total = sum(delta.values()) - delta.get("guest", 0) - delta.get("guest_nice", 0)
        idle = delta.get("idle", 0) + delta.get("iowait", 0)
        if total <= 0:
            return None
        return round(max(0.0, min(100.0, 100 * (total - idle) / total)), 1)

    def __call__(self):
        total = psutil.cpu_times()
        cores = psutil.cpu_times(percpu=True)
        usage = self._usage(self.previous_total, total)
        per_core = [self._usage(self.previous_cores[index], core)
                    if self.previous_cores is not None and index < len(self.previous_cores)
                    else None for index, core in enumerate(cores)]
        self.previous_total, self.previous_cores = total, cores
        try:
            load = psutil.getloadavg()
        except (AttributeError, OSError, NotImplementedError):
            load = (None, None, None)
        try:
            frequencies = psutil.cpu_freq(percpu=True)
        except (AttributeError, OSError, NotImplementedError):
            frequencies = None
        return {
            "usage_percent": usage,
            "per_core_percent": per_core,
            "per_core_scaling_governor": [scaling_governor(index) for index in range(len(cores))],
            "logical_cores": psutil.cpu_count(logical=True),
            "physical_cores": psutil.cpu_count(logical=False),
            "load_average": dict(zip(("1m", "5m", "15m"), load)),
            "per_core_frequency_mhz": [
                {"current": freq.current, "min": freq.min or None, "max": freq.max or None}
                for freq in frequencies
            ] if frequencies else None,
        }


# A sampler owns its own collector; this callable remains available to existing callers.
collect_cpu = CPUCollector()
