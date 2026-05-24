from __future__ import annotations

import sys
import time

sys.path.insert(0, "/app")

from kafka import KafkaProducer
from locust import User, between, events, task

from shared.data_generator import generate_small_message

_BOOTSTRAP = "kafka:9092"


class KafkaUser(User):
    wait_time = between(0.01, 0.05)

    def on_start(self):
        self._producer = KafkaProducer(
            bootstrap_servers=_BOOTSTRAP,
            acks="all",
            linger_ms=5,
            batch_size=16384,
        )

    def on_stop(self):
        try:
            self._producer.close()
        except Exception:
            pass

    @task
    def produce_small(self):
        msg = generate_small_message()
        body = msg.model_dump_json().encode()
        start = time.perf_counter()
        exc = None
        try:
            future = self._producer.send("small-messages", value=body)
            future.get(timeout=30)
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