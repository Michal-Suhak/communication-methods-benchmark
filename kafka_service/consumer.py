from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from kafka import KafkaConsumer as _KafkaConsumer

from shared.metrics import (
    E2E_LATENCY,
    MESSAGE_SIZE,
    REQUEST_COUNT,
    canonical_scenario,
    start_metrics_server,
)

_BOOTSTRAP = "kafka:9092"
_TOPICS = ["small-messages", "large-messages", "echo-messages"]


def main():
    start_metrics_server(9093)
    consumer = _KafkaConsumer(
        *_TOPICS,
        bootstrap_servers=_BOOTSTRAP,
        group_id="benchmark-group",
        # latest: świeży/zrestartowany konsument widzi tylko nowe wiadomości,
        # nie odtwarza zaległości z poprzednich runów (chroni e2e latency).
        auto_offset_reset="latest",
        # Commit okresowy zamiast po każdej wiadomości — nie ogranicza throughputu.
        enable_auto_commit=True,
        auto_commit_interval_ms=1000,
        max_poll_records=500,
    )
    print(f"Kafka consumer started, consuming {_TOPICS}", flush=True)
    for msg in consumer:
        scenario = canonical_scenario(msg.topic)
        try:
            data = json.loads(msg.value)
            if isinstance(data, dict) and "timestamp" in data:
                latency = time.time() - data["timestamp"]
                E2E_LATENCY.labels(method="kafka", scenario=scenario).observe(latency)
            MESSAGE_SIZE.labels(method="kafka", scenario=scenario).observe(len(msg.value))
            REQUEST_COUNT.labels(method="kafka", scenario=scenario, status="success").inc()
        except Exception as exc:
            REQUEST_COUNT.labels(method="kafka", scenario=scenario, status="error").inc()
            print(f"Error processing message: {exc}", flush=True)


if __name__ == "__main__":
    main()
