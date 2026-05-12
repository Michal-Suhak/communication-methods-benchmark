#!/bin/bash
set -euo pipefail

echo "=========================================="
echo "  Benchmark: Communication Methods in Distributed Systems"
echo "=========================================="

# 1. Build Docker images
echo "[1/7] Building Docker images..."
docker compose build

# 2. Start infrastructure
echo "[2/7] Starting infrastructure..."
docker compose up -d rabbitmq zookeeper kafka prometheus grafana
echo "Waiting 30s for brokers to initialise..."
sleep 30

# 3. Start test services
echo "[3/7] Starting test services..."
docker compose up -d rest-server grpc-server graphql-server amqp-consumer kafka-consumer
echo "Waiting 15s for services to initialise..."
sleep 15

# 4. Health checks
echo "[4/7] Running health checks..."
for svc in rest-server graphql-server; do
    host=$(echo "$svc" | tr '-' '-')
    port=8001
    [[ "$svc" == "graphql-server" ]] && port=8003
    curl -sf "http://localhost:${port}/api/health" > /dev/null && echo "  $svc OK" || echo "  $svc WARN"
done

# 5. Run load tests
echo "[5/7] Running load tests..."
docker compose run --rm locust bash /app/run_all_scenarios.sh

# 6. Collect and analyse results
echo "[6/7] Collecting and analysing results..."
python scripts/collect_results.py
python scripts/analyze_results.py
python scripts/generate_charts.py

# 7. Summary
echo "[7/7] Done!"
echo "  Grafana:    http://localhost:3000"
echo "  Prometheus: http://localhost:9090"
echo "  Locust UI:  http://localhost:8089"
echo "  Results:    ./results/"
