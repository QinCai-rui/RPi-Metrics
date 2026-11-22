import asyncio
import hmac
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from agent.metrics.sampler import MetricsSampler


@asynccontextmanager
async def lifespan(app: FastAPI):
    sampler = MetricsSampler()
    app.state.sampler = sampler
    app.state.activity_token = os.environ.get("FLEETMUSTER_ACTIVITY_TOKEN", "").encode()
    sampler.start()
    try:
        yield
    finally:
        await asyncio.to_thread(sampler.stop)


app = FastAPI(title="fleetmuster Agent", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/v1/metrics")
def get_metrics(request: Request):
    sampler = request.app.state.sampler
    token = getattr(request.app.state, "activity_token", b"")
    if (token and request.client and request.client.host in {"127.0.0.1", "::1"}
            and hmac.compare_digest(request.headers.get("X-Fleetmuster-Activity", "").encode(), token)):
        sampler.keep_active(seconds=12)
    return sampler.snapshot()
