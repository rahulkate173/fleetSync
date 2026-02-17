#!/bin/bash
# fleetSync - Run all services (WSL/Linux)
# Usage: ./run.sh [server|frontend|pathway|kafka|all]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load .env if exists
[ -f .env ] && export $(grep -v '^#' .env | xargs)

run_server() {
  echo "Starting fleetSync server..."
  (cd server && pip install -q -r requirements.txt && uvicorn main:app --host 0.0.0.0 --port 8000) &
}

run_frontend() {
  echo "Starting fleetSync frontend..."
  npm install && npm run dev &
}

run_pathway() {
  echo "Starting Pathway engine..."
  (cd pathway && pip install -q -r requirements.txt && python engine.py) &
}

run_kafka() {
  echo "Starting Kafka (Docker)..."
  docker-compose up -d zookeeper kafka
  sleep 5
  echo "Kafka ready. Create topic: docker exec -it fleetsync-kafka-1 kafka-topics --create --topic fleetsync-gps --bootstrap-server localhost:9092"
}

case "${1:-all}" in
  server)  run_server ;;
  frontend) run_frontend ;;
  pathway) run_pathway ;;
  kafka)   run_kafka ;;
  all)
    run_kafka
    sleep 5
    run_server
    sleep 3
    run_pathway
    sleep 2
    run_frontend
    wait
    ;;
  *) echo "Usage: ./run.sh [server|frontend|pathway|kafka|all]" ;;
esac
