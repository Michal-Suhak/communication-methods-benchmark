#!/bin/bash
set -euo pipefail

# ============================================================================
# Orkiestrator scenariuszy benchmarkowych.
#
# Scenariusze (zgodne z planem KROK 9.1):
#   throughput    — siatka obciążeń 10/100/500/1000, szybki ramp, 5 powtórzeń
#   spike         — nagły skok do 2000 użytkowników (test backpressure/recovery)
#   long_running  — 50 użytkowników przez dłuższy czas (dryf, memory leaks)
#
# Konwencja nazw CSV: <method>_u<USERS>_rep<REP>  (parsowana przez collect_results.py)
#
# Zmienne środowiskowe (override):
#   TEST_DURATION (60)  WARMUP_DURATION (30)  COOLDOWN_DURATION (15)
#   REPETITIONS (5)     SPIKE_REPS (3)        LONG_DURATION (300)  LONG_REPS (1)
#   SCENARIOS ("throughput spike long_running")  — które scenariusze uruchomić
#   USER_LEVELS ("10 100 500 1000")
# ============================================================================

WARMUP_DURATION="${WARMUP_DURATION:-30}"
TEST_DURATION="${TEST_DURATION:-60}"
COOLDOWN_DURATION="${COOLDOWN_DURATION:-15}"
RESULTS_DIR="${RESULTS_DIR:-/app/results}"
REPETITIONS="${REPETITIONS:-5}"
SPIKE_REPS="${SPIKE_REPS:-3}"
LONG_DURATION="${LONG_DURATION:-300}"
LONG_REPS="${LONG_REPS:-1}"
USER_LEVELS="${USER_LEVELS:-10 100 500 1000}"
SCENARIOS="${SCENARIOS:-throughput spike long_running}"

METHODS=("rest" "grpc" "graphql" "amqp" "kafka")
LOCUST_FILES=("locustfile_rest.py" "locustfile_grpc.py" "locustfile_graphql.py" "locustfile_amqp.py" "locustfile_kafka.py")
HOSTS=("http://rest-server:8001" "grpc-server:50051" "http://graphql-server:8003" "amqp://guest:guest@rabbitmq:5672/" "kafka:9092")

mkdir -p "$RESULTS_DIR"

# run_measure <locust_file> <host> <users> <spawn_rate> <duration> <csv_prefix>
run_measure() {
  local lf="$1" host="$2" users="$3" rate="$4" dur="$5" csv="$6"
  echo "  [warmup] ${WARMUP_DURATION}s (odrzucane)..."
  locust -f "$lf" --headless \
    -u "$users" -r "$rate" -t "${WARMUP_DURATION}s" \
    --stop-timeout 10s --host="$host" 2>/dev/null || true

  echo "  [measure] ${dur}s → ${csv}"
  locust -f "$lf" --headless \
    -u "$users" -r "$rate" -t "${dur}s" \
    --stop-timeout 10s \
    --csv="$csv" \
    --host="$host"

  echo "  [cooldown] ${COOLDOWN_DURATION}s..."
  sleep "$COOLDOWN_DURATION"
}

for i in "${!METHODS[@]}"; do
  METHOD="${METHODS[$i]}"
  LOCUST_FILE="${LOCUST_FILES[$i]}"
  HOST="${HOSTS[$i]}"

  for SCENARIO in $SCENARIOS; do
    case "$SCENARIO" in
      throughput)
        for USERS in $USER_LEVELS; do
          for REP in $(seq 1 "$REPETITIONS"); do
            echo "=== $METHOD | throughput | users=$USERS | rep=$REP ==="
            # Szybki ramp (spawn ~1s) → minimalny udział fazy ramp w oknie pomiarowym.
            run_measure "$LOCUST_FILE" "$HOST" "$USERS" "$USERS" "$TEST_DURATION" \
              "${RESULTS_DIR}/${METHOD}_u${USERS}_rep${REP}"
          done
        done
        ;;
      spike)
        for REP in $(seq 1 "$SPIKE_REPS"); do
          echo "=== $METHOD | spike | users=2000 | rep=$REP ==="
          # Skok obciążenia: 2000 użytkowników z rampem 200/s (~10s do szczytu).
          run_measure "$LOCUST_FILE" "$HOST" 2000 200 "$TEST_DURATION" \
            "${RESULTS_DIR}/${METHOD}_u2000_rep${REP}"
        done
        ;;
      long_running)
        for REP in $(seq 1 "$LONG_REPS"); do
          echo "=== $METHOD | long_running | users=50 | rep=$REP | ${LONG_DURATION}s ==="
          run_measure "$LOCUST_FILE" "$HOST" 50 50 "$LONG_DURATION" \
            "${RESULTS_DIR}/${METHOD}_u50_rep${REP}"
        done
        ;;
      *)
        echo "Nieznany scenariusz: $SCENARIO" >&2 ;;
    esac
  done
done

echo "Wszystkie scenariusze zakończone. Wyniki w $RESULTS_DIR"
