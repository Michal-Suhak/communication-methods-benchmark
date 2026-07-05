from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import strawberry
from fastapi import FastAPI
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from strawberry.dataloader import DataLoader
from strawberry.extensions import SchemaExtension
from strawberry.fastapi import GraphQLRouter

from shared.data_generator import generate_large_message
from shared.metrics import (
    ACTIVE_CONNECTIONS,
    MESSAGE_SIZE,
    REQUEST_COUNT,
    REQUEST_LATENCY,
    canonical_scenario,
)


class MetricsExtension(SchemaExtension):
    """Measures the full GraphQL operation time (parse + validate + execute),
    not just the resolver body. Measurement scope consistent with REST/gRPC."""

    def on_operation(self):
        ACTIVE_CONNECTIONS.labels(method="graphql").inc()
        start = time.perf_counter()
        try:
            yield
        finally:
            ACTIVE_CONNECTIONS.labels(method="graphql").dec()
        elapsed = time.perf_counter() - start
        ctx = self.execution_context
        scenario = canonical_scenario(ctx.query or "")
        status = "error" if (ctx.result and ctx.result.errors) else "success"
        REQUEST_LATENCY.labels(method="graphql", scenario=scenario).observe(elapsed)
        REQUEST_COUNT.labels(method="graphql", scenario=scenario, status=status).inc()
        # Unified payload-size semantics: large = serialized response data.
        # Serialization happens AFTER the latency observation, but still adds
        # a small (~0.2 ms) overhead to the request lifecycle — acceptable and
        # symmetric across repetitions; without it GraphQL would have no
        # response-size measurement at all (the response shape depends on the
        # fields selected by the client, which is the essence of GraphQL).
        if scenario == "large" and ctx.result and ctx.result.data:
            size = len(json.dumps(ctx.result.data, separators=(",", ":")))
            MESSAGE_SIZE.labels(method="graphql", scenario="large").observe(size)


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


# --- DataLoader: demonstration of the N+1 problem solution -------------------
# Without the DataLoader the `category` field of every item would query the
# source separately (N queries). The DataLoader batches all keys from a single
# request into one `_batch_load_categories` call (1 query).
async def _batch_load_categories(keys: list[str]) -> list[str]:
    # Simulates a single batched category fetch for many tags.
    return [f"category::{k}" for k in keys]


@strawberry.type
class EnrichedItemType:
    name: str
    tags: list[str]

    @strawberry.field
    async def category(self, info) -> str:
        loader: DataLoader = info.context["category_loader"]
        return await loader.load(self.tags[0] if self.tags else "none")


@strawberry.type
class EnrichedResponseType:
    id: str
    items: list[EnrichedItemType]


@strawberry.type
class Query:
    @strawberry.field
    def get_large(self, size_kb: int = 50) -> LargeResponseType:
        large = generate_large_message(size_kb)
        return LargeResponseType(
            id=large.id,
            timestamp=large.timestamp,
            items=[
                ItemType(name=i.name, description=i.description, value=i.value, tags=i.tags)
                for i in large.items
            ],
        )

    @strawberry.field
    def get_large_enriched(self, size_kb: int = 50) -> EnrichedResponseType:
        # Every item has a `category` field resolved through the DataLoader (N+1 demo).
        large = generate_large_message(size_kb)
        return EnrichedResponseType(
            id=large.id,
            items=[EnrichedItemType(name=i.name, tags=i.tags) for i in large.items],
        )

    @strawberry.field
    def health(self) -> bool:
        return True


@strawberry.type
class Mutation:
    @strawberry.mutation
    def send_small(self, id: str, timestamp: float, source: str, payload: str) -> bool:
        size = len(id) + len(source) + len(payload)
        MESSAGE_SIZE.labels(method="graphql", scenario="small").observe(size)
        return True

    @strawberry.mutation
    def echo(self, data: str) -> str:
        return data


schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    extensions=[MetricsExtension],
)


async def get_context() -> dict:
    # Fresh DataLoader per request — batching works within a single request.
    return {"category_loader": DataLoader(load_fn=_batch_load_categories)}


graphql_app = GraphQLRouter(schema, context_getter=get_context)

app = FastAPI(title="GraphQL Benchmark Server")
app.include_router(graphql_app, prefix="/graphql")


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
