from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, start_http_server

# Buckets dobrane pod typowe latencje sieciowe w sieci lokalnej/Docker.
_LATENCY_BUCKETS = [0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]

# Latencja obsługi po stronie serwera (RPC/HTTP) ORAZ latencja publikacji (messaging).
# UWAGA: dla porównań międzyprotokołowych autorytatywnym źródłem jest latencja
# klienta mierzona przez Locust (pełny round-trip). Ta metryka opisuje czas
# przetwarzania po stronie serwera/producenta i nie jest wprost porównywalna
# między protokołami o różnym zakresie pomiaru.
REQUEST_LATENCY = Histogram(
    "request_latency_seconds",
    "Latencja obsługi żądania po stronie serwera/producenta",
    ["method", "scenario"],
    buckets=_LATENCY_BUCKETS,
)

# Latencja end-to-end (od publikacji wiadomości do odebrania przez konsumenta).
# Osobna metryka, aby NIE mieszać jej z latencją publikacji (request_latency_seconds).
E2E_LATENCY = Histogram(
    "e2e_latency_seconds",
    "Latencja end-to-end: od timestampu w wiadomości do odebrania przez konsumenta",
    ["method", "scenario"],
    buckets=_LATENCY_BUCKETS,
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

# Kanoniczne nazwy scenariuszy — wspólne dla wszystkich serwisów, aby serie
# Prometheusa pokrywały się między protokołami (REST/gRPC/GraphQL/AMQP/Kafka).
SCENARIO_SMALL = "small"
SCENARIO_LARGE = "large"
SCENARIO_ECHO = "echo"


def canonical_scenario(raw: str) -> str:
    """Mapuje dowolną etykietę (ścieżka HTTP, nazwa kolejki/topiku, nazwa RPC/operacji)
    na kanoniczne small/large/echo. Zwraca 'other' dla nierozpoznanych (np. health, metrics)."""
    s = raw.lower()
    if "small" in s:
        return SCENARIO_SMALL
    if "large" in s:
        return SCENARIO_LARGE
    if "echo" in s:
        return SCENARIO_ECHO
    return "other"


def start_metrics_server(port: int) -> None:
    start_http_server(port)
