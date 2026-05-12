#!/bin/bash
# Test a single protocol in isolation.
# Usage:
#   bash scripts/test_protocol.sh rest              # 100 users, 60s
#   bash scripts/test_protocol.sh grpc 500          # 500 users, 60s
#   bash scripts/test_protocol.sh kafka 200 120     # 200 users, 120s
#   bash scripts/test_protocol.sh rest 100 60 --ui  # open Locust web UI instead
set -euo pipefail

PROTOCOL=${1:-rest}
USERS=${2:-100}
DURATION=${3:-60}
MODE=${4:-}

RAMP=$((USERS / 10 + 1))
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULTS_DIR="$(cd "$(dirname "$0")/.." && pwd)/results"
mkdir -p "$RESULTS_DIR"

declare -A SERVICE_MAP=(
  [rest]="rest-server"
  [grpc]="grpc-server"
  [graphql]="graphql-server"
  [amqp]="amqp-consumer"
  [kafka]="kafka-consumer"
)

declare -A LOCUST_MAP=(
  [rest]="locustfile_rest.py"
  [grpc]="locustfile_grpc.py"
  [graphql]="locustfile_graphql.py"
  [amqp]="locustfile_amqp.py"
  [kafka]="locustfile_kafka.py"
)

declare -A HOST_MAP=(
  [rest]="http://rest-server:8001"
  [grpc]="grpc-server:50051"
  [graphql]="http://graphql-server:8003"
  [amqp]="amqp://guest:guest@rabbitmq:5672/"
  [kafka]="kafka:9092"
)

declare -A INFRA_MAP=(
  [rest]=""
  [grpc]=""
  [graphql]=""
  [amqp]="rabbitmq"
  [kafka]="zookeeper kafka"
)

if [[ -z "${SERVICE_MAP[$PROTOCOL]+x}" ]]; then
  echo "Unknown protocol: $PROTOCOL"
  echo "Valid: rest | grpc | graphql | amqp | kafka"
  exit 1
fi

SERVICE="${SERVICE_MAP[$PROTOCOL]}"
LOCUST_FILE="${LOCUST_MAP[$PROTOCOL]}"
HOST="${HOST_MAP[$PROTOCOL]}"
INFRA="${INFRA_MAP[$PROTOCOL]}"

echo "================================================"
echo "  Protocol : $PROTOCOL"
echo "  Users    : $USERS  (ramp: $RAMP/s)"
echo "  Duration : ${DURATION}s  (+ 30s warmup)"
echo "  Results  : $RESULTS_DIR/${PROTOCOL}_${USERS}u_${TIMESTAMP}_*.csv"
echo "================================================"

# Ensure monitoring is up (idempotent)
echo "[1/4] Starting monitoring..."
docker compose up -d prometheus grafana

# Ensure protocol-specific infrastructure is up
if [[ -n "$INFRA" ]]; then
  echo "[1/4] Starting infrastructure: $INFRA"
  # shellcheck disable=SC2086
  docker compose up -d $INFRA
  echo "      Waiting 20s for brokers..."
  sleep 20
fi

# Start the service under test
echo "[2/4] Starting service: $SERVICE"
docker compose up -d "$SERVICE"
sleep 5

# Locust web UI mode — open browser, control manually
if [[ "$MODE" == "--ui" ]]; then
  echo "[UI] Locust web UI starting at http://localhost:8089"
  echo "     Press Ctrl+C to stop."
  docker compose run --rm -p 8089:8089 locust \
    locust -f "/app/$LOCUST_FILE" --host="$HOST"
  exit 0
fi

# Headless: warmup then measure
echo "[3/4] Warmup 30s (results discarded)..."
docker compose run --rm locust \
  locust -f "/app/$LOCUST_FILE" --headless \
  -u "$USERS" -r "$RAMP" -t 30s \
  --host="$HOST" 2>/dev/null || true

echo "[4/4] Measuring ${DURATION}s..."
docker compose run --rm \
  -v "$RESULTS_DIR:/app/results" \
  locust \
  locust -f "/app/$LOCUST_FILE" --headless \
  -u "$USERS" -r "$RAMP" -t "${DURATION}s" \
  --csv="/app/results/${PROTOCOL}_${USERS}u_${TIMESTAMP}" \
  --host="$HOST"

echo ""
echo "Done! Files written:"
ls "$RESULTS_DIR/${PROTOCOL}_${USERS}u_${TIMESTAMP}"* 2>/dev/null || true
echo ""
echo "  Grafana overview : http://localhost:3000/d/comm-benchmark-overview"
echo "  Protocol detail  : http://localhost:3000/d/comm-benchmark-detail"
