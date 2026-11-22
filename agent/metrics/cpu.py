import time
import psutil

def collect_cpu():
    psutil.cpu_percent(interval=None)
    psutil.cpu_percent(interval=None, percpu=True)

    # do this so both percentages are measured over the same time period,
    # instead of using `interval=`
    time.sleep(0.2)

    usage = psutil.cpu_percent(interval=None)
    per_core = psutil.cpu_percent(interval=None, percpu=True)
    load_1m, load_5m, load_15m = psutil.getloadavg()
    frequencies = psutil.cpu_freq(percpu=True)

    return {
        "usage_percent": usage,
        "per_core_percent": per_core,
        "logical_cores": psutil.cpu_count(logical=True),
        "physical_cores": psutil.cpu_count(logical=False),
        "load_average": {
            "1m": load_1m,
            "5m": load_5m,
            "15m": load_15m,
        },
        "per_core_frequency_mhz": [
            {
                "current": freq.current,
                "min": freq.min or None,
                "max": freq.max or None,
            }
            for freq in frequencies
        ] if frequencies else None,
    }
