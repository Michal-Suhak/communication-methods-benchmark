"""Maximum-throughput publisher for AMQP/Kafka in native (async/batched) mode.

Unlike the Locust load tests — which publish synchronously (one message, then
wait for the broker acknowledgment) for latency comparability — this script
fires messages as fast as possible using each broker's native batching and
pipelining, i.e. the mode in which these systems reach their real throughput
ceiling. Delivered throughput is read separately from the consumer side
(request_total counter in Prometheus), so the reported figure reflects messages
actually delivered to and processed by the consumer, not just writes to a local
socket buffer.

Usage (inside the compose network): python throughput_producer.py <method> <seconds>
Prints the number of messages published and the produce rate to stdout.
"""
from __future__ import annotations

import sys
import time

sys.path.insert(0, "/app")

from shared.data_generator import generate_small_message

_EXCHANGE = "benchmark_exchange"


def run_kafka(duration: float) -> int:
    from kafka import KafkaProducer

    producer = KafkaProducer(
        bootstrap_servers="kafka:9092",
        acks="all",
        # Native high-throughput settings: batch aggressively, do not block per message.
        linger_ms=10,
        batch_size=64 * 1024,
    )
    # Pre-serialize once so the measurement reflects broker/pipeline throughput,
    # not the cost of JSON generation on the producer side.
    body = generate_small_message().model_dump_json().encode()
    n = 0
    end = time.time() + duration
    while time.time() < end:
        producer.send("small-messages", value=body)
        n += 1
    producer.flush()
    producer.close()
    return n


def run_amqp(duration: float) -> int:
    import pika

    conn = pika.BlockingConnection(
        pika.ConnectionParameters(
            host="rabbitmq",
            credentials=pika.PlainCredentials("guest", "guest"),
        )
    )
    ch = conn.channel()
    ch.exchange_declare(exchange=_EXCHANGE, exchange_type="direct", durable=True)
    ch.queue_declare(queue="small_messages", durable=True)
    ch.queue_bind(queue="small_messages", exchange=_EXCHANGE, routing_key="small")
    # No per-message confirm: publish is pipelined to the broker at maximum rate.
    body = generate_small_message().model_dump_json().encode()
    props = pika.BasicProperties(delivery_mode=2)
    n = 0
    end = time.time() + duration
    while time.time() < end:
        ch.basic_publish(exchange=_EXCHANGE, routing_key="small", body=body, properties=props)
        n += 1
    conn.close()
    return n


def main() -> None:
    method = sys.argv[1]
    duration = float(sys.argv[2]) if len(sys.argv) > 2 else 30.0
    start = time.time()
    if method == "kafka":
        n = run_kafka(duration)
    elif method == "amqp":
        n = run_amqp(duration)
    else:
        print(f"Unknown method: {method}", file=sys.stderr)
        sys.exit(1)
    elapsed = time.time() - start
    print(f"published={n} elapsed={elapsed:.2f}s produce_rate={n / elapsed:.0f} msg/s")


if __name__ == "__main__":
    main()
