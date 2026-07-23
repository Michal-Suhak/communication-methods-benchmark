"""Measure delivered throughput of AMQP/Kafka publishing in native async mode.

Runs throughput_producer.py inside the compose network for each messaging
method, then reads the consumer-side *delivered* throughput from Prometheus:
the peak sustained rate of the request_total counter incremented by the
consumer per processed message. Reporting the consumer rate (not the producer
rate) means the figure reflects messages actually delivered end-to-end, which
is the honest measure of sustainable throughput.

Writes results/async_throughput.csv. Assumes the messaging brokers and
consumers are already running (docker compose up).
"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

import pandas as pd
import requests

PROM = "http://localhost:9090"
PROJECT = Path(__file__).parent.parent
RESULTS = PROJECT / "results"
METHODS = ["kafka", "amqp"]
DURATION = 30
REPS = 3


def peak_consumer_rate(method: str) -> float:
    """Highest 30 s-averaged consumption rate over the last 2 minutes (msg/s)."""
    q = (
        f'max_over_time(rate(request_total{{method="{method}",scenario="small",'
        f'status="success"}}[30s])[2m:15s])'
    )
    r = requests.get(f"{PROM}/api/v1/query", params={"query": q}, timeout=10).json()
    res = r["data"]["result"]
    return float(res[0]["value"][1]) if res else 0.0


def main() -> None:
    rows = []
    for method in METHODS:
        for rep in range(1, REPS + 1):
            proc = subprocess.run(
                ["docker", "compose", "run", "--rm", "--no-deps", "locust", "python",
                 "/app/throughput_producer.py", method, str(DURATION)],
                capture_output=True, text=True, cwd=str(PROJECT),
            )
            produced_line = proc.stdout.strip()
            produce_rate = 0.0
            for tok in produced_line.split():
                if tok.startswith("produce_rate="):
                    produce_rate = float(tok.split("=")[1])
            time.sleep(5)  # let the consumer drain in-flight messages
            consumer_rate = peak_consumer_rate(method)
            print(f"{method} rep{rep}: {produced_line} | consumer_rate={consumer_rate:.0f} msg/s")
            rows.append({
                "method": method,
                "rep": rep,
                "produce_rate_msgs": produce_rate,
                "consumer_rate_msgs": consumer_rate,
            })
            time.sleep(10)  # cooldown between runs
    df = pd.DataFrame(rows)
    out = RESULTS / "async_throughput.csv"
    df.to_csv(out, index=False)
    print(f"\nSaved → {out}")
    summary = df.groupby("method")[["produce_rate_msgs", "consumer_rate_msgs"]].mean().round(0)
    print(summary.to_string())


if __name__ == "__main__":
    main()
