# Communication Methods Benchmark

A reproducible, containerized environment for benchmarking five communication methods: **REST/HTTP**, **gRPC**, **GraphQL**, **AMQP (RabbitMQ)**, and **Apache Kafka**.

## Tech stack

| Method | Transport | Port | Framework |
|--------|-----------|------|-----------|
| REST | HTTP/1.1 | 8001 | FastAPI + httpx |
| gRPC | HTTP/2 | 50051 | grpcio |
| GraphQL | HTTP/1.1 | 8003 | Strawberry + FastAPI |
| AMQP | AMQP 0-9-1 | 5672 | pika + RabbitMQ |
| Kafka | TCP | 9092 | kafka-python + Confluent Kafka |

Load testing: [Locust](https://locust.io) · Metrics: [Prometheus](https://prometheus.io) · Visualization: [Grafana](https://grafana.com)

## Requirements

- Docker ≥ 24
- Docker Compose ≥ 2.20
- 8 GB RAM (all services running simultaneously)

## Quick start

```bash
# Infrastructure + monitoring
docker compose up -d --build rabbitmq zookeeper kafka prometheus grafana cadvisor
# Wait ~30s

# Application services + Locust
docker compose up -d --build rest-server grpc-server graphql-server amqp-consumer kafka-consumer locust
```

Open **http://localhost:8089** — select a protocol with the checkbox and click Start.

Full run documentation: [`RUN_INSTRUCTION.md`](RUN_INSTRUCTION.md)

## UIs

| What | URL |
|----|-----|
| Locust (protocol picker) | http://localhost:8089 |
| Grafana — All Methods Overview | http://localhost:3000/d/comm-benchmark-overview |
| Grafana — Protocol Detail | http://localhost:3000/d/comm-benchmark-detail |
| Prometheus | http://localhost:9090 |
| RabbitMQ Management | http://localhost:15672 (guest / guest) |

## Project structure

```
.
├── shared/                     # Shared Pydantic models, data generator, Prometheus metrics
├── rest/                       # FastAPI server
├── grpc_service/               # gRPC server; .proto in proto/
├── graphql_service/            # Strawberry server (metrics extension + DataLoader)
├── amqp_service/               # RabbitMQ consumer (pika, sync)
├── kafka_service/              # Kafka consumer (kafka-python, sync)
├── load_tests/                 # Locust — one file per protocol + locustfile_all.py
├── monitoring/
│   ├── prometheus/prometheus.yml
│   └── grafana/dashboards/     # benchmark.json (overview) + protocol_detail.json
├── scripts/
│   ├── run_experiment.sh       # Full experiment: build → tests → analysis
│   ├── test_protocol.sh        # Headless test for a single protocol
│   ├── collect_results.py      # Merges Locust CSVs + Prometheus data
│   ├── analyze_results.py      # Statistics: Kruskal-Wallis, percentiles, 95% CI
│   └── generate_charts.py      # 300 DPI PNG/SVG charts
├── results/                    # CSVs and charts (output)
├── docker-compose.yml
└── RUN_INSTRUCTION.md
```

## Test scenarios

Implemented in `load_tests/run_all_scenarios.sh` (selectable via `SCENARIOS`, all values overridable via env vars):

| Scenario | Payload | Users | Duration | Repetitions |
|----------|---------|-------|----------|-------------|
| `throughput` (small + large task mix) | ~100–500 B / 50 and 100 KB | 10 → 100 → 500 → 1000 (`USER_LEVELS`) | 60 s / level (`TEST_DURATION`) | 5 (`REPETITIONS`) |
| `spike` | ~100–500 B / 50 and 100 KB | 2000 (ramp 200/s ≈ 10 s) | 60 s peak | 3 (`SPIKE_REPS`) |
| `long_running` | ~100–500 B / 50 and 100 KB | 50 (steady) | 300 s default, plan: 1800 s (`LONG_DURATION`) | 3 (`LONG_REPS`) |

Before each measurement: 30 s warmup (results discarded; separate Locust process — client connection pools are cold-started in the measured run), 15 s cooldown after the test.

Every protocol uses the same two-class user structure: a *small* user class (wait 0.01–0.05 s; small messages, plus a 256 B `echo` task for the request-reply protocols) and a *large* user class (wait 0.1–0.5 s; 50 and 100 KB payloads). The echo variant runs only for REST/gRPC/GraphQL — a broker publish has no reply to echo back.

### What latency means per protocol

- **REST / gRPC / GraphQL** — full client-side round-trip (Locust).
- **AMQP** — publish → broker confirm (publisher confirms enabled), **Kafka** — publish → broker ACK (`acks=all`). Comparable to each other, *not* directly to round-trip numbers.
- **End-to-end latency** (producer → consumer) is a separate metric `e2e_latency_seconds` reported by consumers.

## Prometheus metrics

| Metric | Type | Labels |
|--------|------|--------|
| `request_latency_seconds` | Histogram | `method`, `scenario` — server-side processing time (full request scope: REST middleware, gRPC interceptor, GraphQL schema extension) |
| `e2e_latency_seconds` | Histogram | `method`, `scenario` — producer→consumer end-to-end (AMQP/Kafka) |
| `request_total` | Counter | `method`, `scenario`, `status` |
| `message_size_bytes` | Histogram | `method`, `scenario` — serialized benchmark payload: `small` = client request/message, `large` = server response/message |
| `active_connections` | Gauge | `method` — servers: in-flight requests; consumers: 1 while broker connection is active |

Scenario labels are canonical across all services: `small` / `large` / `echo`. Scrape interval: 5 s. Metrics ports: REST=8001, gRPC=9091, GraphQL=8003, AMQP=9092, Kafka=9093. Container CPU/RAM comes from **cAdvisor** (port 8080).

> For cross-protocol latency comparisons use the client-side (Locust) numbers — Locust reports **milliseconds**, Prometheus histograms are in **seconds**.

## Results analysis

Grafana serves real-time observation *during* a test run. The scripts below are a separate post-processing pipeline that runs *after* all experiments finish: they merge raw Locust CSVs with Prometheus time-series, run statistical significance tests (Kruskal-Wallis, IQR outlier removal, 95% CI), and produce publication-quality 300 DPI charts suitable for a thesis — something Grafana cannot do.

```bash
python scripts/collect_results.py   # output: locust_unified.csv + prometheus_metrics.csv + container_resources.csv
python scripts/analyze_results.py   # output: statistical_analysis[_by_level].csv + significance tests + post-hoc
python scripts/generate_charts.py   # output: results/charts/*.png + *.svg
```

| File | Contents |
|------|----------|
| `locust_unified.csv` | Merged Locust statistics (latency in **ms**) |
| `prometheus_metrics.csv` | Prometheus time-series (latency in **s**), window matched to test run |
| `statistical_analysis.csv` | Per-method stats over `Aggregated` rows: mean, median, std, IQR, p50/p95/p99 (same-percentile mean across repetitions), 95% CI |
| `statistical_analysis_by_level.csv` | Same stats per (method, users) — source for the thesis result tables |
| `significance_by_level.csv` + `posthoc_*_u{N}.csv` | Omnibus + post-hoc per load level |
| `container_resources.csv` | Container CPU (cores) and RAM (bytes) time series from cAdvisor |
| `significance_tests.csv` | Omnibus test (ANOVA or Kruskal-Wallis, chosen by Shapiro normality) |
| `posthoc_tukey.csv` / `posthoc_dunn.csv` | Pairwise post-hoc comparisons (Tukey HSD / Dunn with Bonferroni) |
| `results/charts/` | latency_bar, latency_boxplot, heatmap, radar, throughput_vs_users, latency_vs_users, latency_vs_payload, spike_timeline, longrun_timeline, resources |

## Resource limits (per container)

| Service | CPU | RAM |
|---------|-----|-----|
| REST / gRPC / GraphQL | 2.0 | 512 MB |
| AMQP / Kafka consumer | 2.0 | 512 MB |
| RabbitMQ / Kafka | 2.0 | 1 GB |
| Locust | 2.0 | 1 GB |
| Prometheus | 0.5 | 512 MB |
| Grafana | 0.5 | 256 MB |
| cAdvisor | 0.5 | 256 MB |

## gRPC code generation

Protobuf stubs are generated automatically during `docker build`:

```bash
# Locally (outside Docker):
pip install grpcio-tools
python -m grpc_tools.protoc -I grpc_service/proto \
    --python_out=grpc_service/generated \
    --grpc_python_out=grpc_service/generated \
    grpc_service/proto/benchmark.proto
```