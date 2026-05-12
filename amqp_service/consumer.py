from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Callable, Awaitable

sys.path.insert(0, str(Path(__file__).parent.parent))

import aio_pika

from shared.metrics import MESSAGE_SIZE, REQUEST_COUNT, REQUEST_LATENCY, start_metrics_server

_AMQP_URL = "amqp://guest:guest@rabbitmq:5672/"


class AMQPConsumer:
    def __init__(self, amqp_url: str = _AMQP_URL) -> None:
        self._url = amqp_url
        self._connection: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.Channel | None = None

    async def connect(self):
        self._connection = await aio_pika.connect_robust(self._url)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=100)

    async def start_consuming(self, queue_name: str, callback: Callable[[dict], Awaitable[None]]):
        queue = await self._channel.declare_queue(queue_name, durable=True)

        async def on_message(message: aio_pika.IncomingMessage):
            async with message.process(requeue=False):
                try:
                    data = json.loads(message.body)
                    receive_ts = time.time()
                    if "timestamp" in data:
                        latency = receive_ts - data["timestamp"]
                        REQUEST_LATENCY.labels(method="amqp", scenario=queue_name).observe(latency)
                    MESSAGE_SIZE.labels(method="amqp", scenario=queue_name).observe(len(message.body))
                    await callback(data)
                    REQUEST_COUNT.labels(method="amqp", scenario=queue_name, status="success").inc()
                except Exception as exc:
                    REQUEST_COUNT.labels(method="amqp", scenario=queue_name, status="error").inc()
                    print(f"Error processing message: {exc}", flush=True)

        await queue.consume(on_message)

    async def stop(self):
        if self._connection:
            await self._connection.close()


async def _noop_callback(data: dict):
    pass


async def main():
    start_metrics_server(9092)
    consumer = AMQPConsumer()
    await consumer.connect()
    print("AMQP consumer connected, waiting for messages...", flush=True)
    for queue_name in ("small_messages", "large_messages", "echo_messages"):
        await consumer.start_consuming(queue_name, _noop_callback)
    # Keep running
    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
