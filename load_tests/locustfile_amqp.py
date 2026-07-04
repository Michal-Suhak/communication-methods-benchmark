from __future__ import annotations

import sys
import time

sys.path.insert(0, "/app")

import pika
from locust import User, between, events, task

from shared.data_generator import generate_large_message, generate_small_message

_EXCHANGE = "benchmark_exchange"
_DEFAULT_URL = "amqp://guest:guest@rabbitmq:5672/"


class AMQPUser(User):
    wait_time = between(0.01, 0.05)

    def on_start(self):
        url = self.host or _DEFAULT_URL
        # --host może być podane jako amqp://... (honorujemy je); inaczej domyślne.
        params = pika.URLParameters(url) if "://" in url else pika.ConnectionParameters(host=url)
        self._connection = pika.BlockingConnection(params)
        self._channel = self._connection.channel()
        # Publisher confirms: basic_publish blokuje do potwierdzenia brokera,
        # dzięki czemu mierzymy publish→ACK (symetrycznie do acks=all w Kafce),
        # a nie tylko zapis do lokalnego bufora socketu.
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

    @task(3)
    def publish_small(self):
        body = generate_small_message().model_dump_json().encode()
        self._publish("publish_small", "small", body)

    @task(1)
    def publish_large(self):
        body = generate_large_message(50).model_dump_json().encode()
        self._publish("publish_large", "large", body)
