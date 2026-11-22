import logging
from datetime import datetime, timezone

from fastapi import FastAPI

from agent.metrics.cpu import collect_cpu
from agent.metrics.disk import collect_disk
from agent.metrics.memory import collect_memory
from agent.metrics.network import collect_network
from agent.metrics.system import collect_system

app = FastAPI(title="fleetmuster Agent", version="1.0.0")
logger = logging.getLogger(__name__)

def collect_metrics(collector):
    try:
        return collector()
    except Exception as e:
        logger.error(f"Error collecting metrics from {collector.__name__}: {e}")
        return None

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/v1/metrics")
def get_metrics():
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cpu": collect_metrics(collect_cpu),
        "memory": collect_metrics(collect_memory),
        "disk": collect_metrics(collect_disk),
        "network": collect_metrics(collect_network),
        "system": collect_metrics(collect_system),
    }
    