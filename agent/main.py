import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from agent.metrics.sampler import MetricsSampler


@asynccontextmanager
async def lifespan(app: FastAPI):
    sampler = MetricsSampler()
    app.state.sampler = sampler
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
    return request.app.state.sampler.snapshot()
