from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx

from shared.models import BenchmarkResult, SmallMessage

_BASE_URL = "http://graphql-server:8003"
_GRAPHQL_URL = f"{_BASE_URL}/graphql"


class GraphQLBenchmarkClient:
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

    async def _gql(self, query: str, variables: dict | None = None) -> tuple[dict, int]:
        payload = {"query": query, "variables": variables or {}}
        response = await self._client.post("/graphql", json=payload)
        return response.json(), len(response.content)

    async def send_small(self, msg: SmallMessage) -> BenchmarkResult:
        mutation = """
        mutation($id: String!, $timestamp: Float!, $source: String!, $payload: String!) {
            sendSmall(id: $id, timestamp: $timestamp, source: $source, payload: $payload)
        }
        """
        payload_size = len(msg.model_dump_json())
        start = time.perf_counter()
        data, _ = await self._gql(mutation, {"id": msg.id, "timestamp": msg.timestamp, "source": msg.source, "payload": msg.payload})
        elapsed_ms = (time.perf_counter() - start) * 1000
        success = "errors" not in data
        return BenchmarkResult(method="graphql", scenario="small", latency_ms=elapsed_ms, timestamp=time.time(), success=success, payload_size_bytes=payload_size)

    async def request_large_full(self, size_kb: int = 50) -> BenchmarkResult:
        query = """
        query($sizeKb: Int!) {
            getLarge(sizeKb: $sizeKb) { id timestamp items { name description value tags } }
        }
        """
        start = time.perf_counter()
        data, response_size = await self._gql(query, {"sizeKb": size_kb})
        elapsed_ms = (time.perf_counter() - start) * 1000
        success = "errors" not in data
        return BenchmarkResult(method="graphql", scenario="large_full", latency_ms=elapsed_ms, timestamp=time.time(), success=success, payload_size_bytes=response_size)

    async def request_large_partial(self, size_kb: int = 50) -> BenchmarkResult:
        query = """
        query($sizeKb: Int!) {
            getLarge(sizeKb: $sizeKb) { id items { name value } }
        }
        """
        start = time.perf_counter()
        data, response_size = await self._gql(query, {"sizeKb": size_kb})
        elapsed_ms = (time.perf_counter() - start) * 1000
        success = "errors" not in data
        return BenchmarkResult(method="graphql", scenario="large_partial", latency_ms=elapsed_ms, timestamp=time.time(), success=success, payload_size_bytes=response_size)

    async def echo(self, data: str) -> BenchmarkResult:
        mutation = 'mutation($data: String!) { echo(data: $data) }'
        payload_size = len(data)
        start = time.perf_counter()
        result, _ = await self._gql(mutation, {"data": data})
        elapsed_ms = (time.perf_counter() - start) * 1000
        success = "errors" not in result
        return BenchmarkResult(method="graphql", scenario="echo", latency_ms=elapsed_ms, timestamp=time.time(), success=success, payload_size_bytes=payload_size)
