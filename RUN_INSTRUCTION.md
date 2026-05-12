# Run Instructions

## Testing strategy

Test **one protocol at a time** — eliminates CPU/RAM resource contention.  
Use the **Locust web UI** for exploration, **headless CLI** for actual measurements.

---

## Step 1 — First run

```bash
# Infrastructure + monitoring
docker compose up -d --build rabbitmq zookeeper kafka prometheus grafana
# Wait ~30s for Kafka and RabbitMQ

# Application services + Locust
docker compose up -d --build rest-server grpc-server graphql-server amqp-consumer kafka-consumer locust
```

On subsequent runs without code changes, skip `--build`.

---

## Step 2 — Interactive testing (web UI)

Open **http://localhost:8089** — Locust has checkboxes for protocol selection (`--class-picker`):

| Class | Protocol |
|---|---|
| `RestSmallMessageUser`, `RestLargeResponseUser` | REST |
| `GrpcUser` | gRPC |
| `GraphQLSmallUser`, `GraphQLLargeUser` | GraphQL |
| `AMQPUser` | AMQP / RabbitMQ |
| `KafkaUser` | Kafka |

Select classes → set user count → **Start**.

---

## Step 3 — Headless testing (measurements for thesis)

```bash
# bash scripts/test_protocol.sh <protocol> [users] [duration_s]
bash scripts/test_protocol.sh rest     100 60
bash scripts/test_protocol.sh grpc     100 60
bash scripts/test_protocol.sh graphql  100 60
bash scripts/test_protocol.sh amqp     100 60
bash scripts/test_protocol.sh kafka    100 60
```

Each run: 30 s warmup (discarded) → measurement → CSV in `results/`.

---

## Step 4 — Full automated experiment

```bash
bash scripts/run_experiment.sh
# build → start → all scenarios × 5 repetitions → analysis → charts
```

---

## Step 5 — Results analysis

```bash
python scripts/collect_results.py   # merges Locust + Prometheus CSVs
python scripts/analyze_results.py   # p50–p99, Kruskal-Wallis, 95% CI
python scripts/generate_charts.py   # 300 DPI PNG/SVG for thesis
```

---

## UIs and dashboards

| What | URL | Login |
|---|---|---|
| **Locust** (class picker) | http://localhost:8089 | — |
| **Grafana — All Methods** | http://localhost:3000/d/comm-benchmark-overview | admin / admin |
| **Grafana — Protocol Detail** | http://localhost:3000/d/comm-benchmark-detail | admin / admin |
| Prometheus | http://localhost:9090 | — |
| RabbitMQ Management | http://localhost:15672 | guest / guest |

**Grafana — All Methods**: stat panels with p50+rps per method, time series p50/p95/p99, bar ranking.  
**Grafana — Protocol Detail**: `Protocol` dropdown, p50/p75/p95/p99 view, breakdown per scenario.

---

## Method colors (consistent across all charts)

| REST | gRPC | GraphQL | AMQP | Kafka |
|---|---|---|---|---|
| `#2196F3` | `#4CAF50` | `#E91E63` | `#FF9800` | `#9C27B0` |