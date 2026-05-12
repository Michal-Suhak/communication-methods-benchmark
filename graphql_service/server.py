from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import strawberry
from fastapi import FastAPI
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from strawberry.fastapi import GraphQLRouter

from shared.data_generator import generate_large_message
from shared.metrics import (
    MESSAGE_SIZE,
    REQUEST_COUNT,
    REQUEST_LATENCY,
)


@strawberry.type
class ItemType:
    name: str
    description: str
    value: float
    tags: list[str]


@strawberry.type
class LargeResponseType:
    id: str
    timestamp: float
    items: list[ItemType]


@strawberry.type
class Query:
    @strawberry.field
    def get_large(self, size_kb: int = 50) -> LargeResponseType:
        start = time.perf_counter()
        large = generate_large_message(size_kb)
        result = LargeResponseType(
            id=large.id,
            timestamp=large.timestamp,
            items=[
                ItemType(name=i.name, description=i.description, value=i.value, tags=i.tags)
                for i in large.items
            ],
        )
        elapsed = time.perf_counter() - start
        REQUEST_LATENCY.labels(method="graphql", scenario="large").observe(elapsed)
        REQUEST_COUNT.labels(method="graphql", scenario="large", status="success").inc()
        return result

    @strawberry.field
    def health(self) -> bool:
        return True


@strawberry.type
class Mutation:
    @strawberry.mutation
    def send_small(self, id: str, timestamp: float, source: str, payload: str) -> bool:
        start = time.perf_counter()
        size = len(id) + len(source) + len(payload)
        elapsed = time.perf_counter() - start
        REQUEST_LATENCY.labels(method="graphql", scenario="small").observe(elapsed)
        REQUEST_COUNT.labels(method="graphql", scenario="small", status="success").inc()
        MESSAGE_SIZE.labels(method="graphql", scenario="small").observe(size)
        return True

    @strawberry.mutation
    def echo(self, data: str) -> str:
        return data


schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_app = GraphQLRouter(schema)

app = FastAPI(title="GraphQL Benchmark Server")
app.include_router(graphql_app, prefix="/graphql")


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
