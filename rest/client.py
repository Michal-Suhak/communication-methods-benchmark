from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx

from shared.models import BenchmarkResult, SmallMessage

_BASE_URL = "http://rest-server:8001"


class RestBenchmarkClient:
    def __init__(self, base_url: str = _BASE_URL) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=30.0,
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self._client.aclose()

    async def send_small_message(self, msg: SmallMessage) -> BenchmarkResult:
        payload = msg.model_dump_json().encode()
        start = time.perf_counter()
        response = await self._client.post("/api/small", content=payload, headers={"content-type": "application/json"})
        elapsed_ms = (time.perf_counter() - start) * 1000
        return BenchmarkResult(
            method="rest",
            scenario="small",
            latency_ms=elapsed_ms,
            timestamp=time.time(),
            success=response.is_success,
            payload_size_bytes=len(payload),
        )

    async def request_large_response(self, size_kb: int = 50) -> BenchmarkResult:
        start = time.perf_counter()
        response = await self._client.post(f"/api/large?size_kb={size_kb}")
        elapsed_ms = (time.perf_counter() - start) * 1000
        body = response.content
        return BenchmarkResult(
            method="rest",
            scenario="large",
            latency_ms=elapsed_ms,
            timestamp=time.time(),
            success=response.is_success,
            payload_size_bytes=len(body),
        )

    async def echo(self, data: bytes) -> BenchmarkResult:
        start = time.perf_counter()
        response = await self._client.post("/api/echo", content=data)
        elapsed_ms = (time.perf_counter() - start) * 1000
        return BenchmarkResult(
            method="rest",
            scenario="echo",
            latency_ms=elapsed_ms,
            timestamp=time.time(),
            success=response.is_success,
            payload_size_bytes=len(data),
        )
