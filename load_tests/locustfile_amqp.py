from __future__ import annotations

import sys
import time

sys.path.insert(0, "/app")

import pika
from locust import User, between, events, task

from shared.data_generator import generate_small_message

_EXCHANGE = "benchmark_exchange"


class AMQPUser(User):
    wait_time = between(0.01, 0.05)

    def on_start(self):
        params = pika.ConnectionParameters(
            host="rabbitmq",
            credentials=pika.PlainCredentials("guest", "guest"),
        )
        self._connection = pika.BlockingConnection(params)
        self._channel = self._connection.channel()
        self._channel.exchange_declare(
            exchange=_EXCHANGE, exchange_type="direct", durable=True
        )
        self._channel.queue_declare(queue="small_messages", durable=True)
        self._channel.queue_bind(
            queue="small_messages", exchange=_EXCHANGE, routing_key="small"
        )

    def on_stop(self):
        try:
            self._connection.close()
        except Exception:
            pass

    @task
    def publish_small(self):
        msg = generate_small_message()
        body = msg.model_dump_json().encode()
        start = time.perf_counter()
        exc = None
        try:
            self._channel.basic_publish(
                exchange=_EXCHANGE,
                routing_key="small",
                body=body,
                properties=pika.BasicProperties(delivery_mode=2),
            )
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
