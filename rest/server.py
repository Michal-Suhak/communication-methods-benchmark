from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Request
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from shared.data_generator import generate_large_message
from shared.metrics import (
    ACTIVE_CONNECTIONS,
    MESSAGE_SIZE,
    REQUEST_COUNT,
    REQUEST_LATENCY,
    canonical_scenario,
)
from shared.models import LargeMessage, SmallMessage

app = FastAPI(title="REST Benchmark Server")

# Ścieżki pomijane w pomiarze: scrape Prometheusa i health-check nie są ruchem
# benchmarkowym i zaniżałyby/zaburzały histogram latencji oraz licznik żądań.
_SKIP_PATHS = {"/metrics", "/api/health"}


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    if request.url.path in _SKIP_PATHS:
        return await call_next(request)
    method_label = "rest"
    scenario = canonical_scenario(request.url.path)
    ACTIVE_CONNECTIONS.labels(method=method_label).inc()
    start = time.perf_counter()
    try:
        response = await call_next(request)
    finally:
        ACTIVE_CONNECTIONS.labels(method=method_label).dec()
    elapsed = time.perf_counter() - start
    REQUEST_LATENCY.labels(method=method_label, scenario=scenario).observe(elapsed)
    # Unified payload-size semantics: small = client request payload,
    # large/echo = server response payload (see shared/metrics.py).
    if scenario == "small":
        size_source = request.headers.get("content-length")
    else:
        size_source = response.headers.get("content-length")
    if size_source:
        MESSAGE_SIZE.labels(method=method_label, scenario=scenario).observe(int(size_source))
    status = "success" if response.status_code < 400 else "error"
    REQUEST_COUNT.labels(method=method_label, scenario=scenario, status=status).inc()
    # JSON log to stdout
    print(
        json.dumps(
            {
                "ts": time.time(),
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "latency_ms": round(elapsed * 1000, 3),
            }
        ),
        flush=True,
    )
    return response


@app.post("/api/small")
async def post_small(msg: SmallMessage):
    return {"id": msg.id, "accepted": True, "server_timestamp": time.time()}


@app.post("/api/large")
async def post_large(size_kb: int = 50) -> LargeMessage:
    return generate_large_message(size_kb)


@app.post("/api/echo")
async def echo(request: Request):
    body = await request.body()
    return Response(content=body, media_type="application/octet-stream")


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
