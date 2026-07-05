from __future__ import annotations

import sys
import time

sys.path.insert(0, "/app")

from kafka import KafkaProducer
from locust import User, between, events, task

from shared.data_generator import (
    LARGE_PAYLOAD_BASE_KB,
    LARGE_PAYLOAD_EXTENDED_KB,
    generate_large_message,
    generate_small_message,
)

_DEFAULT_BOOTSTRAP = "kafka:9092"


class KafkaUser(User):
    wait_time = between(0.01, 0.05)

    def on_start(self):
        self._producer = KafkaProducer(
            bootstrap_servers=self.host or _DEFAULT_BOOTSTRAP,
            acks="all",
            linger_ms=5,
            batch_size=16384,
        )

    def on_stop(self):
        try:
            self._producer.close()
        except Exception:
            pass

    def _produce(self, name: str, topic: str, body: bytes):
        start = time.perf_counter()
        exc = None
        try:
            future = self._producer.send(topic, value=body)
            future.get(timeout=30)
        except Exception as e:
            exc = e
        elapsed_ms = (time.perf_counter() - start) * 1000
        events.request.fire(
            request_type="kafka",
            name=name,
            response_time=elapsed_ms,
            response_length=len(body),
            exception=exc,
        )

    @task(6)
    def produce_small(self):
        body = generate_small_message().model_dump_json().encode()
        self._produce("produce_small", "small-messages", body)

    def _produce_large(self, size_kb: int):
        body = generate_large_message(size_kb).model_dump_json().encode()
        self._produce(f"produce_large[{size_kb}kb]", "large-messages", body)

    @task(1)
    def produce_large_base(self):
        self._produce_large(LARGE_PAYLOAD_BASE_KB)

    @task(1)
    def produce_large_extended(self):
        self._produce_large(LARGE_PAYLOAD_EXTENDED_KB)
