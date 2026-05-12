# Communication Methods Benchmark

Powtarzalne, konteneryzowane środowisko do porównania wydajności pięciu metod komunikacji: **REST/HTTP**, **gRPC**, **GraphQL**, **AMQP (RabbitMQ)** i **Apache Kafka**.

## Stos technologiczny

| Metoda | Transport | Port | Framework |
|--------|-----------|------|-----------|
| REST | HTTP/1.1 | 8001 | FastAPI + httpx |
| gRPC | HTTP/2 | 50051 | grpcio |
| GraphQL | HTTP/1.1 | 8003 | Strawberry + FastAPI |
| AMQP | AMQP 0-9-1 | 5672 | aio-pika + RabbitMQ |
| Kafka | TCP | 9092 | aiokafka + Confluent Kafka |

Testy obciążeniowe: [Locust](https://locust.io) · Metryki: [Prometheus](https://prometheus.io) · Wizualizacja: [Grafana](https://grafana.com)

## Wymagania

- Docker ≥ 24
- Docker Compose ≥ 2.20
- 8 GB RAM (wszystkie serwisy jednocześnie)

## Szybki start

```bash
# Infrastruktura + monitoring
docker compose up -d --build rabbitmq zookeeper kafka prometheus grafana
# Czekaj ~30s

# Serwisy + Locust
docker compose up -d --build rest-server grpc-server graphql-server amqp-consumer kafka-consumer locust
```

Otwórz **http://localhost:8089** — wybierz protokół checkboxem i naciśnij Start.

Pełna dokumentacja uruchamiania: [`RUN_INSTRUCTION.md`](RUN_INSTRUCTION.md)

## UI

| Co | URL |
|----|-----|
| Locust (wybór protokołu) | http://localhost:8089 |
| Grafana — All Methods Overview | http://localhost:3000/d/comm-benchmark-overview |
| Grafana — Protocol Detail | http://localhost:3000/d/comm-benchmark-detail |
| Prometheus | http://localhost:9090 |
| RabbitMQ Management | http://localhost:15672 (guest / guest) |

## Struktura projektu

```
.
├── shared/                     # Wspólne modele Pydantic, generator danych, metryki Prometheus
├── rest/                       # Serwer FastAPI + klient httpx
├── grpc_service/               # Serwer + klient gRPC; .proto w proto/
├── graphql_service/            # Serwer Strawberry + klient
├── amqp_service/               # Producent + konsument RabbitMQ (aio-pika)
├── kafka_service/              # Producent + konsument Kafka (aiokafka)
├── load_tests/                 # Locust — jeden plik per protokół + locustfile_all.py
├── monitoring/
│   ├── prometheus/prometheus.yml
│   └── grafana/dashboards/     # benchmark.json (overview) + protocol_detail.json
├── scripts/
│   ├── run_experiment.sh       # Pełny eksperyment: build → testy → analiza
│   ├── test_protocol.sh        # Headless test jednego protokołu
│   ├── collect_results.py      # Scala CSVy Locusta + dane Prometheus
│   ├── analyze_results.py      # Statystyki: Kruskal-Wallis, percentyle, CI 95%
│   └── generate_charts.py      # Wykresy PNG/SVG 300 DPI
├── results/                    # CSVy i wykresy (output)
├── docker-compose.yml
└── RUN_INSTRUCTION.md
```

## Scenariusze testowe

| # | Scenariusz | Payload | Użytkownicy | Czas |
|---|------------|---------|-------------|------|
| 1 | Małe wiadomości, wysoka częstotliwość | ~100–500 B | 10 → 100 → 500 → 1000 | 60 s / poziom |
| 2 | Duże odpowiedzi | ~50–100 KB | 10 → 50 → 100 | 60 s / poziom |
| 3 | Spike test | ~100–500 B | 10 → 2000 (ramp 10 s) | 30 s peak |
| 4 | Długotrwałe połączenia | ~100–500 B | 50 (stały) | 30 min |

Każdy scenariusz powtarzany **5 razy**. Przed każdym pomiarem: 30 s warmup (wyniki odrzucane), 15 s cooldown po teście.

## Metryki Prometheus

| Metryka | Typ | Etykiety |
|---------|-----|---------|
| `request_latency_seconds` | Histogram | `method`, `scenario` |
| `request_total` | Counter | `method`, `scenario`, `status` |
| `message_size_bytes` | Histogram | `method`, `scenario` |
| `active_connections` | Gauge | `method` |

Scrape interval: 5 s. Porty metryk: REST=8001, gRPC=9091, GraphQL=8003, AMQP=9092, Kafka=9093.

## Analiza wyników

```bash
python scripts/collect_results.py   # wynik: results/locust_unified.csv + prometheus_metrics.csv
python scripts/analyze_results.py   # wynik: statistical_analysis.csv + significance_tests.csv
python scripts/generate_charts.py   # wynik: results/charts/*.png + *.svg
```

| Plik | Zawartość |
|------|-----------|
| `locust_unified.csv` | Scalone statystyki Locusta |
| `prometheus_metrics.csv` | Szeregi czasowe Prometheus |
| `statistical_analysis.csv` | Średnia, mediana, std, IQR, p50–p99, CI 95% |
| `significance_tests.csv` | Test Kruskal-Wallis |
| `results/charts/` | latency_bar, latency_boxplot, heatmap, radar |

## Limity zasobów (per kontener)

| Serwis | CPU | RAM |
|--------|-----|-----|
| REST / gRPC / GraphQL | 2.0 | 512 MB |
| AMQP / Kafka consumer | 2.0 | 512 MB |
| RabbitMQ / Kafka | 2.0 | 1 GB |
| Locust | 2.0 | 1 GB |
| Prometheus | 0.5 | 512 MB |
| Grafana | 0.5 | 256 MB |

## Generowanie kodu gRPC

Protobuf stubs generowane automatycznie podczas `docker build`:

```bash
# Lokalnie (poza Dockerem):
pip install grpcio-tools
python -m grpc_tools.protoc -I grpc_service/proto \
    --python_out=grpc_service/generated \
    --grpc_python_out=grpc_service/generated \
    grpc_service/proto/benchmark.proto
```
