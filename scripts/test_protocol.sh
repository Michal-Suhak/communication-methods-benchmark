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

case "$PROTOCOL" in
  rest)     SERVICE="rest-server";    LOCUST_FILE="locustfile_rest.py";    HOST="http://rest-server:8001";          INFRA="" ;;
  grpc)     SERVICE="grpc-server";    LOCUST_FILE="locustfile_grpc.py";    HOST="grpc-server:50051";                INFRA="" ;;
  graphql)  SERVICE="graphql-server"; LOCUST_FILE="locustfile_graphql.py"; HOST="http://graphql-server:8003";       INFRA="" ;;
  amqp)     SERVICE="amqp-consumer";  LOCUST_FILE="locustfile_amqp.py";    HOST="amqp://guest:guest@rabbitmq:5672/"; INFRA="rabbitmq" ;;
  kafka)    SERVICE="kafka-consumer"; LOCUST_FILE="locustfile_kafka.py";   HOST="kafka:9092";                       INFRA="zookeeper kafka" ;;
  *)
    echo "Unknown protocol: $PROTOCOL"
    echo "Valid: rest | grpc | graphql | amqp | kafka"
    exit 1 ;;
esac

echo "================================================"
echo "  Protocol : $PROTOCOL"
echo "  Users    : $USERS  (ramp: $RAMP/s)"
echo "  Duration : ${DURATION}s  (+ 30s warmup)"
echo "  Results  : $RESULTS_DIR/${PROTOCOL}_${USERS}u_${TIMESTAMP}_*.csv"
echo "================================================"

echo "[1/4] Starting monitoring..."
docker compose up -d prometheus grafana

if [[ -n "$INFRA" ]]; then
  echo "[1/4] Starting infrastructure: $INFRA"
  # shellcheck disable=SC2086
  docker compose up -d $INFRA
  echo "      Waiting 20s for brokers..."
  sleep 20
fi

echo "[2/4] Starting service: $SERVICE"
docker compose up -d "$SERVICE"
sleep 5

if [[ "$MODE" == "--ui" ]]; then
  echo "[UI] Locust web UI starting at http://localhost:8089"
  echo "     Press Ctrl+C to stop."
  docker compose run --rm -p 8089:8089 locust \
    locust -f "/app/$LOCUST_FILE" --host="$HOST"
  exit 0
fi

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