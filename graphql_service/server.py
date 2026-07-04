from __future__ import annotations

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
    MESSAGE_SIZE,
    REQUEST_COUNT,
    REQUEST_LATENCY,
    canonical_scenario,
)


class MetricsExtension(SchemaExtension):
    """Mierzy pełny czas operacji GraphQL (parsowanie + walidacja + wykonanie),
    a nie tylko ciało resolvera. Zakres pomiaru spójny z REST/gRPC (pełna obsługa)."""

    def on_operation(self):
        start = time.perf_counter()
        yield
        ctx = self.execution_context
        scenario = canonical_scenario(ctx.query or "")
        status = "error" if (ctx.result and ctx.result.errors) else "success"
        REQUEST_LATENCY.labels(method="graphql", scenario=scenario).observe(
            time.perf_counter() - start
        )
        REQUEST_COUNT.labels(method="graphql", scenario=scenario, status=status).inc()


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


# --- DataLoader: demonstracja rozwiązania problemu N+1 -----------------------
# Bez DataLoadera pole `category` każdego itemu odpytywałoby źródło osobno
# (N zapytań). DataLoader batchuje wszystkie klucze z jednego żądania w jedno
# wywołanie `_batch_load_categories` (1 zapytanie).
async def _batch_load_categories(keys: list[str]) -> list[str]:
    # Symulacja jednego batchowego pobrania kategorii dla wielu tagów.
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
        # Każdy item ma pole `category` rozwiązywane przez DataLoader (demo N+1).
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
    # Nowy DataLoader na każde żądanie — batchowanie działa w obrębie jednego żądania.
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
