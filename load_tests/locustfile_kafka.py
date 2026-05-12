from __future__ import annotations

import asyncio
import sys
import time

sys.path.insert(0, "/app")

from aiokafka import AIOKafkaProducer
from locust import User, between, events, task

from shared.data_generator import generate_small_message

_BOOTSTRAP = "kafka:9092"


class KafkaUser(User):
    wait_time = between(0.01, 0.05)

    def on_start(self):
        self._loop = asyncio.new_event_loop()
        self._loop.run_until_complete(self._start_producer())

    def _run(self, coro):
        return self._loop.run_until_complete(coro)

    async def _start_producer(self):
        self._producer = AIOKafkaProducer(
            bootstrap_servers=_BOOTSTRAP,
            acks="all",
            linger_ms=5,
            max_batch_size=16384,
        )
        await self._producer.start()

    def on_stop(self):
        self._run(self._producer.stop())
        self._loop.close()

    @task
    def produce_small(self):
        msg = generate_small_message()
        body = msg.model_dump_json().encode()
        start = time.perf_counter()
        exc = None
        try:
            self._run(self._producer.send_and_wait("small-messages", value=body))
        except Exception as e:
            exc = e
        elapsed_ms = (time.perf_counter() - start) * 1000
        events.request.fire(
            request_type="kafka",
            name="produce_small",
            response_time=elapsed_ms,
            response_length=len(body),
            exception=exc,
        )
