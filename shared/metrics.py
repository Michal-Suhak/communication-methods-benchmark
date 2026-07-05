from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, start_http_server

# Buckets tuned for typical network latencies on a local/Docker network.
_LATENCY_BUCKETS = [0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]

# Server-side handling latency (RPC/HTTP) AND publish latency (messaging).
# NOTE: for cross-protocol comparisons the authoritative source is the client
# latency measured by Locust (full round-trip). This metric describes the
# server/producer processing time and is not directly comparable between
# protocols with a different measurement scope.
REQUEST_LATENCY = Histogram(
    "request_latency_seconds",
    "Server/producer-side request handling latency",
    ["method", "scenario"],
    buckets=_LATENCY_BUCKETS,
)

# End-to-end latency (message publish → consumption by the consumer).
# Separate metric so it is never mixed with publish latency (request_latency_seconds).
# Extended buckets: under spike load the queue/log backlog can push e2e far beyond
# the 5 s ceiling of the request-latency buckets.
_E2E_BUCKETS = _LATENCY_BUCKETS + [10.0, 30.0, 60.0]
E2E_LATENCY = Histogram(
    "e2e_latency_seconds",
    "End-to-end latency: from the message timestamp to consumption",
    ["method", "scenario"],
    buckets=_E2E_BUCKETS,
)

REQUEST_COUNT = Counter(
    "request_total",
    "Total number of requests",
    ["method", "scenario", "status"],
)

# Unified semantics (shared by all protocols): size of the SERIALIZED BENCHMARK
# PAYLOAD in bytes —
#   scenario=small → payload sent BY THE CLIENT (SmallMessage / request),
#   scenario=large → payload returned BY THE SERVER (LargeMessage / response),
#   scenario=echo  → size of the echoed data.
# Differences between protocols reflect ONLY the serialization format
# (JSON vs protobuf vs selected GraphQL fields), not a different measurement definition.
MESSAGE_SIZE = Histogram(
    "message_size_bytes",
    "Serialized benchmark payload size in bytes",
    ["method", "scenario"],
)

# Servers (REST/gRPC/GraphQL): number of requests/operations currently being
# processed (in-flight) — grows under saturation, exposes queueing.
# Consumers (AMQP/Kafka): 1 while the broker connection is active, 0 after close.
ACTIVE_CONNECTIONS = Gauge(
    "active_connections",
    "Servers: in-flight requests; consumers: broker connection status",
    ["method"],
)

# Canonical scenario names — shared by all services so that Prometheus series
# align across protocols (REST/gRPC/GraphQL/AMQP/Kafka).
SCENARIO_SMALL = "small"
SCENARIO_LARGE = "large"
SCENARIO_ECHO = "echo"


def canonical_scenario(raw: str) -> str:
    """Map any label (HTTP path, queue/topic name, RPC/operation name) to the
    canonical small/large/echo. Returns 'other' for unrecognized ones
    (e.g. health, metrics)."""
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
