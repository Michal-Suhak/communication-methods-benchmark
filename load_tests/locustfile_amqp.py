from __future__ import annotations

import sys
import time

sys.path.insert(0, "/app")

import pika
from locust import User, between, events, task

from shared.data_generator import (
    LARGE_PAYLOAD_BASE_KB,
    LARGE_PAYLOAD_EXTENDED_KB,
    generate_large_message,
    generate_small_message,
)

_EXCHANGE = "benchmark_exchange"
_DEFAULT_URL = "amqp://guest:guest@rabbitmq:5672/"


class AMQPUserBase(User):
    abstract = True

    def on_start(self):
        url = self.host or _DEFAULT_URL
        # --host may be given as amqp://... (honoured); otherwise fall back to default.
        params = pika.URLParameters(url) if "://" in url else pika.ConnectionParameters(host=url)
        self._connection = pika.BlockingConnection(params)
        self._channel = self._connection.channel()
        # Publisher confirms: basic_publish blocks until the broker ACK, so we
        # measure publish→ACK (symmetric to acks=all in Kafka) instead of just
        # a write to the local socket buffer.
        self._channel.confirm_delivery()
        self._channel.exchange_declare(exchange=_EXCHANGE, exchange_type="direct", durable=True)
        for queue_name, routing_key in (("small_messages", "small"), ("large_messages", "large")):
            self._channel.queue_declare(queue=queue_name, durable=True)
            self._channel.queue_bind(queue=queue_name, exchange=_EXCHANGE, routing_key=routing_key)

    def on_stop(self):
        try:
            self._connection.close()
        except Exception:
            pass

    def _publish(self, name: str, routing_key: str, body: bytes):
        start = time.perf_counter()
        exc = None
        try:
            self._channel.basic_publish(
                exchange=_EXCHANGE,
                routing_key=routing_key,
                body=body,
                properties=pika.BasicProperties(delivery_mode=2),
            )
        except Exception as e:
            exc = e
        elapsed_ms = (time.perf_counter() - start) * 1000
        events.request.fire(
            request_type="amqp",
            name=name,
            response_time=elapsed_ms,
            response_length=len(body),
            exception=exc,
        )


class AMQPSmallUser(AMQPUserBase):
    wait_time = between(0.01, 0.05)

    @task
    def publish_small(self):
        body = generate_small_message().model_dump_json().encode()
        self._publish("publish_small", "small", body)


class AMQPLargeUser(AMQPUserBase):
    wait_time = between(0.1, 0.5)

    def _publish_large(self, size_kb: int):
        body = generate_large_message(size_kb).model_dump_json().encode()
        self._publish(f"publish_large[{size_kb}kb]", "large", body)

    @task(1)
    def publish_large_base(self):
        self._publish_large(LARGE_PAYLOAD_BASE_KB)

    @task(1)
    def publish_large_extended(self):
        self._publish_large(LARGE_PAYLOAD_EXTENDED_KB)
