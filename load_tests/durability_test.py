"""Durability subtest: zero message loss under consumer failure (AMQP / Kafka).

Demonstrates the core guarantee of message brokers that request-reply protocols
cannot provide: a consumer crash does not lose messages. N messages with unique
sequential IDs are published; a first consumer processes roughly half and then
"crashes" (its connection/offsets close mid-work); a second consumer resumes and
drains the rest. We verify that every published ID was ultimately consumed
(loss = 0) and report the number of duplicates, which reflects the at-least-once
delivery semantics (uncommitted/unacknowledged in-flight messages are redelivered).

- Kafka: the consumer resumes from the last committed offset of the durable log.
- AMQP:  unacknowledged messages on a durable queue are returned and redelivered.

Runs inside the compose network. Usage: python durability_test.py <method> [N]
"""
from __future__ import annotations

import sys
import time

_TOPIC = "durability-test"
_COMMIT_EVERY = 1000


def test_kafka(n: int) -> dict:
    from kafka import KafkaConsumer, KafkaProducer

    producer = KafkaProducer(bootstrap_servers="kafka:9092", acks="all")
    for i in range(n):
        producer.send(_TOPIC, value=str(i).encode())
    producer.flush()
    producer.close()

    group = f"dur-{int(time.time())}"

    def consumer():
        return KafkaConsumer(
            _TOPIC,
            bootstrap_servers="kafka:9092",
            group_id=group,
            auto_offset_reset="earliest",
            enable_auto_commit=False,
            consumer_timeout_ms=5000,
        )

    received: list[int] = []
    half = n // 2

    # Consumer 1: process ~half, committing periodically, then "crash" (close)
    # without committing the last in-flight batch.
    c1 = consumer()
    since_commit = 0
    for msg in c1:
        received.append(int(msg.value))
        since_commit += 1
        if since_commit >= _COMMIT_EVERY:
            c1.commit()
            since_commit = 0
        if len(received) >= half:
            break  # crash: the last (< _COMMIT_EVERY) messages stay uncommitted
    c1.close()

    # Consumer 2: same group resumes from the last committed offset.
    c2 = consumer()
    for msg in c2:
        received.append(int(msg.value))
    c2.close()
    return _summarise(n, received)


def test_amqp(n: int) -> dict:
    import pika

    params = pika.ConnectionParameters(
        host="rabbitmq", credentials=pika.PlainCredentials("guest", "guest")
    )
    conn = pika.BlockingConnection(params)
    ch = conn.channel()
    ch.queue_declare(queue=_TOPIC, durable=True)
    ch.queue_purge(_TOPIC)
    for i in range(n):
        ch.basic_publish(
            exchange="", routing_key=_TOPIC, body=str(i).encode(),
            properties=pika.BasicProperties(delivery_mode=2),
        )
    conn.close()

    received: list[int] = []
    half = n // 2

    # Consumer 1: manual ack; ack up to ~half then "crash" — prefetched but
    # unacknowledged messages are returned to the durable queue by the broker.
    conn1 = pika.BlockingConnection(params)
    ch1 = conn1.channel()
    ch1.basic_qos(prefetch_count=200)
    for frame, _props, body in ch1.consume(_TOPIC, inactivity_timeout=5):
        if body is None:
            break
        received.append(int(body))
        if len(received) < half:
            ch1.basic_ack(frame.delivery_tag)
        else:
            break  # crash before acking the rest
    conn1.close()

    # Consumer 2: drains the queue, including messages redelivered after the crash.
    conn2 = pika.BlockingConnection(params)
    ch2 = conn2.channel()
    for frame, _props, body in ch2.consume(_TOPIC, inactivity_timeout=5):
        if body is None:
            break
        received.append(int(body))
        ch2.basic_ack(frame.delivery_tag)
    conn2.close()
    return _summarise(n, received)


def _summarise(n: int, received: list[int]) -> dict:
    produced = set(range(n))
    got = set(received)
    return {
        "produced": n,
        "consumed_unique": len(got),
        "lost": len(produced - got),
        "duplicates": len(received) - len(got),
    }


def main() -> None:
    method = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 20000
    if method == "kafka":
        r = test_kafka(n)
    elif method == "amqp":
        r = test_amqp(n)
    else:
        print(f"Unknown method: {method}", file=sys.stderr)
        sys.exit(1)
    print(
        f"{method}: produced={r['produced']} consumed_unique={r['consumed_unique']} "
        f"lost={r['lost']} duplicates={r['duplicates']}"
    )


if __name__ == "__main__":
    main()
