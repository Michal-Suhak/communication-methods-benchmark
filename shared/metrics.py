from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, start_http_server

REQUEST_LATENCY = Histogram(
    "request_latency_seconds",
    "Latencja żądań",
    ["method", "scenario"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

REQUEST_COUNT = Counter(
    "request_total",
    "Całkowita liczba żądań",
    ["method", "scenario", "status"],
)

MESSAGE_SIZE = Histogram(
    "message_size_bytes",
    "Rozmiar wiadomości w bajtach",
    ["method", "scenario"],
)

ACTIVE_CONNECTIONS = Gauge(
    "active_connections",
    "Aktywne połączenia",
    ["method"],
)


def start_metrics_server(port: int) -> None:
    start_http_server(port)
