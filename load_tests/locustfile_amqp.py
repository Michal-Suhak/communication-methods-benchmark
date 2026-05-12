from __future__ import annotations

import asyncio
import sys
import time

sys.path.insert(0, "/app")

import aio_pika
from locust import User, between, events, task

from shared.data_generator import generate_small_message

_AMQP_URL = "amqp://guest:guest@rabbitmq:5672/"
_EXCHANGE = "benchmark_exchange"


class AMQPUser(User):
    wait_time = between(0.01, 0.05)

    def on_start(self):
        self._loop = asyncio.new_event_loop()
        self._loop.run_until_complete(self._connect())

    def _run(self, coro):
        return self._loop.run_until_complete(coro)

    async def _connect(self):
        self._connection = await aio_pika.connect_robust(_AMQP_URL)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=100)
        self._exchange = await self._channel.declare_exchange(
            _EXCHANGE, aio_pika.ExchangeType.DIRECT, durable=True
        )
        queue = await self._channel.declare_queue("small_messages", durable=True)
        await queue.bind(self._exchange, routing_key="small")

    def on_stop(self):
        self._run(self._connection.close())
        self._loop.close()

    @task
    def publish_small(self):
        msg = generate_small_message()
        body = msg.model_dump_json().encode()
        message = aio_pika.Message(
            body=body,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        start = time.perf_counter()
        exc = None
        try:
            self._run(self._exchange.publish(message, routing_key="small"))
        except Exception as e:
            exc = e
        elapsed_ms = (time.perf_counter() - start) * 1000
        events.request.fire(
            request_type="amqp",
            name="publish_small",
            response_time=elapsed_ms,
            response_length=len(body),
            exception=exc,
        )
