#!/bin/bash
set -euo pipefail

WARMUP_DURATION=30
TEST_DURATION=60
COOLDOWN_DURATION=15
RESULTS_DIR=/app/results
REPETITIONS=3

METHODS=("rest" "grpc" "graphql" "amqp" "kafka")
LOCUST_FILES=("locustfile_rest.py" "locustfile_grpc.py" "locustfile_graphql.py" "locustfile_amqp.py" "locustfile_kafka.py")
HOSTS=("http://rest-server:8001" "grpc-server:50051" "http://graphql-server:8003" "amqp://rabbitmq:5672" "kafka:9092")

mkdir -p "$RESULTS_DIR"

for i in "${!METHODS[@]}"; do
  METHOD="${METHODS[$i]}"
  LOCUST_FILE="${LOCUST_FILES[$i]}"
  HOST="${HOSTS[$i]}"

  for USERS in 10 100 500; do
    for REP in $(seq 1 "$REPETITIONS"); do
      echo "=== Method: $METHOD | Users: $USERS | Rep: $REP ==="

      echo "  [warmup] ${WARMUP_DURATION}s..."
      locust -f "$LOCUST_FILE" --headless \
        -u "$USERS" -r "$((USERS / 10 + 1))" \
        -t "${WARMUP_DURATION}s" \
        --host="$HOST" 2>/dev/null || true

      echo "  [measure] ${TEST_DURATION}s..."
      locust -f "$LOCUST_FILE" --headless \
        -u "$USERS" -r "$((USERS / 10 + 1))" \
        -t "${TEST_DURATION}s" \
        --csv="${RESULTS_DIR}/${METHOD}_u${USERS}_rep${REP}" \
        --host="$HOST"

      echo "  [cooldown] ${COOLDOWN_DURATION}s..."
      sleep "$COOLDOWN_DURATION"
    done
  done
done

echo "All scenarios completed. Results saved to $RESULTS_DIR"
