from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from aiokafka import AIOKafkaProducer as _AIOKafkaProducer

from shared.metrics import MESSAGE_SIZE, REQUEST_COUNT, REQUEST_LATENCY, start_metrics_server
from shared.models import BenchmarkResult, LargeMessage, SmallMessage

_BOOTSTRAP = "kafka:9092"


class KafkaProducer:
    def __init__(self, bootstrap_servers: str = _BOOTSTRAP) -> None:
        self._bootstrap = bootstrap_servers
        self._producer: _AIOKafkaProducer | None = None

    async def start(self):
        self._producer = _AIOKafkaProducer(
            bootstrap_servers=self._bootstrap,
            acks="all",
            linger_ms=5,
            max_batch_size=16384,
            compression_type=None,
        )
        await self._producer.start()

    async def _send(self, topic: str, body: bytes, scenario: str) -> BenchmarkResult:
        start = time.perf_counter()
        await self._producer.send_and_wait(topic, value=body)
        elapsed_ms = (time.perf_counter() - start) * 1000
        REQUEST_LATENCY.labels(method="kafka", scenario=scenario).observe(elapsed_ms / 1000)
        REQUEST_COUNT.labels(method="kafka", scenario=scenario, status="success").inc()
        MESSAGE_SIZE.labels(method="kafka", scenario=scenario).observe(len(body))
        return BenchmarkResult(
            method="kafka",
            scenario=scenario,
            latency_ms=elapsed_ms,
            timestamp=time.time(),
            success=True,
            payload_size_bytes=len(body),
        )

    async def send_small(self, msg: SmallMessage) -> BenchmarkResult:
        return await self._send("small-messages", msg.model_dump_json().encode(), "small")

    async def send_large(self, msg: LargeMessage) -> BenchmarkResult:
        return await self._send("large-messages", msg.model_dump_json().encode(), "large")

    async def send_echo(self, data: bytes) -> BenchmarkResult:
        return await self._send("echo-messages", data, "echo")

    async def stop(self):
        if self._producer:
            await self._producer.stop()


if __name__ == "__main__":
    start_metrics_server(9093)

    async def main():
        producer = KafkaProducer()
        await producer.start()
        print("Kafka producer started", flush=True)
        while True:
            await asyncio.sleep(60)

    asyncio.run(main())
