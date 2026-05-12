from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Callable, Awaitable

sys.path.insert(0, str(Path(__file__).parent.parent))

from aiokafka import AIOKafkaConsumer as _AIOKafkaConsumer

from shared.metrics import MESSAGE_SIZE, REQUEST_COUNT, REQUEST_LATENCY, start_metrics_server

_BOOTSTRAP = "kafka:9092"


class KafkaConsumer:
    def __init__(self, bootstrap_servers: str = _BOOTSTRAP) -> None:
        self._bootstrap = bootstrap_servers
        self._consumer: _AIOKafkaConsumer | None = None

    async def start(self, topics: list[str]):
        self._consumer = _AIOKafkaConsumer(
            *topics,
            bootstrap_servers=self._bootstrap,
            group_id="benchmark-group",
            auto_offset_reset="earliest",
            enable_auto_commit=False,
            max_poll_records=500,
        )
        await self._consumer.start()

    async def consume(self, callback: Callable[[dict], Awaitable[None]]):
        async for msg in self._consumer:
            try:
                data = json.loads(msg.value)
                receive_ts = time.time()
                if "timestamp" in data:
                    latency = receive_ts - data["timestamp"]
                    REQUEST_LATENCY.labels(method="kafka", scenario=msg.topic).observe(latency)
                MESSAGE_SIZE.labels(method="kafka", scenario=msg.topic).observe(len(msg.value))
                await callback(data)
                await self._consumer.commit()
                REQUEST_COUNT.labels(method="kafka", scenario=msg.topic, status="success").inc()
            except Exception as exc:
                REQUEST_COUNT.labels(method="kafka", scenario=msg.topic, status="error").inc()
                print(f"Error processing message: {exc}", flush=True)

    async def stop(self):
        if self._consumer:
            await self._consumer.stop()


async def _noop_callback(data: dict):
    pass


async def main():
    start_metrics_server(9093)
    consumer = KafkaConsumer()
    topics = ["small-messages", "large-messages", "echo-messages"]
    await consumer.start(topics)
    print(f"Kafka consumer started, consuming {topics}", flush=True)
    await consumer.consume(_noop_callback)


if __name__ == "__main__":
    asyncio.run(main())
