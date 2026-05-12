from __future__ import annotations

import uuid
from pydantic import BaseModel, Field


class SmallMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float
    source: str
    payload: str


class Item(BaseModel):
    name: str
    description: str
    value: float
    tags: list[str]
    metadata: dict[str, str]


class LargeMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float
    items: list[Item]


class BenchmarkResult(BaseModel):
    method: str
    scenario: str
    latency_ms: float
    timestamp: float
    success: bool
    payload_size_bytes: int
