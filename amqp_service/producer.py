from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import aio_pika

from shared.metrics import MESSAGE_SIZE, REQUEST_COUNT, REQUEST_LATENCY, start_metrics_server
from shared.models import BenchmarkResult, LargeMessage, SmallMessage

_AMQP_URL = "amqp://guest:guest@rabbitmq:5672/"
_EXCHANGE = "benchmark_exchange"


class AMQPProducer:
    def __init__(self, amqp_url: str = _AMQP_URL) -> None:
        self._url = amqp_url
        self._connection: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.Channel | None = None
        self._exchange: aio_pika.Exchange | None = None

    async def connect(self):
        self._connection = await aio_pika.connect_robust(self._url)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=100)
        self._exchange = await self._channel.declare_exchange(
            _EXCHANGE, aio_pika.ExchangeType.DIRECT, durable=True
        )
        for queue_name, routing_key in [
            ("small_messages", "small"),
            ("large_messages", "large"),
            ("echo_messages", "echo"),
        ]:
            queue = await self._channel.declare_queue(queue_name, durable=True)
            await queue.bind(self._exchange, routing_key=routing_key)

    async def _publish(self, routing_key: str, body: bytes, scenario: str) -> BenchmarkResult:
        message = aio_pika.Message(
            body=body,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        start = time.perf_counter()
        await self._exchange.publish(message, routing_key=routing_key)
        elapsed_ms = (time.perf_counter() - start) * 1000
        REQUEST_LATENCY.labels(method="amqp", scenario=scenario).observe(elapsed_ms / 1000)
        REQUEST_COUNT.labels(method="amqp", scenario=scenario, status="success").inc()
        MESSAGE_SIZE.labels(method="amqp", scenario=scenario).observe(len(body))
        return BenchmarkResult(
            method="amqp",
            scenario=scenario,
            latency_ms=elapsed_ms,
            timestamp=time.time(),
            success=True,
            payload_size_bytes=len(body),
        )

    async def send_small(self, msg: SmallMessage) -> BenchmarkResult:
        return await self._publish("small", msg.model_dump_json().encode(), "small")

    async def send_large(self, msg: LargeMessage) -> BenchmarkResult:
        return await self._publish("large", msg.model_dump_json().encode(), "large")

    async def send_echo(self, data: bytes) -> BenchmarkResult:
        return await self._publish("echo", data, "echo")

    async def close(self):
        if self._connection:
            await self._connection.close()


if __name__ == "__main__":
    start_metrics_server(9092)

    async def main():
        producer = AMQPProducer()
        await producer.connect()
        print("AMQP producer connected", flush=True)
        # Keep alive to expose metrics
        while True:
            await asyncio.sleep(60)

    asyncio.run(main())
