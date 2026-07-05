from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pika

from shared.metrics import (
    ACTIVE_CONNECTIONS,
    E2E_LATENCY,
    MESSAGE_SIZE,
    REQUEST_COUNT,
    canonical_scenario,
    start_metrics_server,
)

_EXCHANGE = "benchmark_exchange"
_QUEUES = [
    ("small_messages", "small"),
    ("large_messages", "large"),
    ("echo_messages", "echo"),
]


def main():
    start_metrics_server(9092)
    params = pika.ConnectionParameters(
        host="rabbitmq",
        credentials=pika.PlainCredentials("guest", "guest"),
        heartbeat=600,
        blocked_connection_timeout=300,
    )
    connection = pika.BlockingConnection(params)
    channel = connection.channel()

    # Konsument sam deklaruje topologię i wiąże kolejki — niezależnie od kolejności
    # startu producenta. Purge usuwa zaległości z poprzednich runów (chroni e2e latency).
    channel.exchange_declare(exchange=_EXCHANGE, exchange_type="direct", durable=True)
    for queue_name, routing_key in _QUEUES:
        channel.queue_declare(queue=queue_name, durable=True)
        channel.queue_bind(queue=queue_name, exchange=_EXCHANGE, routing_key=routing_key)
        channel.queue_purge(queue_name)
    channel.basic_qos(prefetch_count=100)

    def on_message(chan, method, properties, body):
        scenario = canonical_scenario(method.routing_key)
        try:
            data = json.loads(body)
            if isinstance(data, dict) and "timestamp" in data:
                latency = time.time() - data["timestamp"]
                E2E_LATENCY.labels(method="amqp", scenario=scenario).observe(latency)
            MESSAGE_SIZE.labels(method="amqp", scenario=scenario).observe(len(body))
            REQUEST_COUNT.labels(method="amqp", scenario=scenario, status="success").inc()
        except Exception as exc:
            REQUEST_COUNT.labels(method="amqp", scenario=scenario, status="error").inc()
            print(f"Error processing message: {exc}", flush=True)
        finally:
            # ACK po przetworzeniu (auto_ack=False)
            chan.basic_ack(delivery_tag=method.delivery_tag)

    for queue_name, _ in _QUEUES:
        channel.basic_consume(queue=queue_name, on_message_callback=on_message, auto_ack=False)

    print("AMQP consumer connected, waiting for messages...", flush=True)
    # Gauge semantics for consumers: 1 while the broker connection is active.
    ACTIVE_CONNECTIONS.labels(method="amqp").set(1)
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()
    finally:
        ACTIVE_CONNECTIONS.labels(method="amqp").set(0)
        connection.close()


if __name__ == "__main__":
    main()
