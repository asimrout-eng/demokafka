
## Firebolt Core + Kafka Demo

This demo sets up:
- Firebolt Core locally (single node via Docker)
- Apache Kafka (single broker) via Docker Compose
- A Python producer sending dummy events to Kafka (`demo.events`)
- A Python sink that consumes from Kafka and inserts into Firebolt Core over HTTP
- A FastAPI dashboard to visualize Kafka produced count and Firebolt ingested row count

Prereqs:
- Docker Desktop installed and running on macOS
- curl

### 1) Install and start Firebolt Core

Run Firebolt Core as a Docker container and expose the HTTP SQL endpoint on port 3473.

```bash
docker rm -f firebolt-core >/dev/null 2>&1 || true
mkdir -p ./firebolt-core-data

docker run -d --name firebolt-core \
  --ulimit memlock=8589934592:8589934592 \
  --security-opt seccomp=unconfined \
  -v "$(pwd)/firebolt-core-data:/firebolt-core/volume" \
  -p 0.0.0.0:3473:3473 \
  ghcr.io/firebolt-db/firebolt-core:preview-rc

# Wait a few seconds, then verify:
curl -s http://localhost:3473 --data-binary 'SELECT 42'
```

### 2) Initialize demo schema (database + table)

```bash
bash firebolt/init.sh
```

This creates database `demo_db` and fact table `demo_events`.

### 3) Start Kafka + producer + sink + dashboard

```bash
# Create env from template
[ -f .env ] || cp env.example .env

# Start everything
docker compose up -d --build
```

- Kafka broker: `localhost:9092`
- Producer sends random demo events to topic `demo.events`
- Sink consumes `demo.events` and inserts rows into `demo_db.demo_events`
- Dashboard (FastAPI) is available at: http://localhost:8000

### 4) Verify the pipeline end-to-end

- Check row count in Firebolt Core:

```bash
curl -s "http://localhost:3473?database=demo_db" \
  --data-binary 'SELECT COUNT(*) FROM demo_events;'
```

- Peek Kafka topic messages:

```bash
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic demo.events \
  --from-beginning \
  --max-messages 5
```

- View sink/producer logs:

```bash
docker logs -f confluentdemo-sink-1   # inserts into Firebolt Core
docker logs -f confluentdemo-producer-1
```

- Open the dashboard (Web UI):

  - UI: http://localhost:8000
  - Metrics JSON: http://localhost:8000/metrics

The dashboard shows:
- Kafka messages produced (computed from topic offsets)
- Rows ingested in Firebolt (`SELECT COUNT(*) FROM demo_events`)

### 5) Tuning and troubleshooting

- Adjust producer rate:
  - Edit `EVENTS_PER_SECOND` in `.env` and run `docker compose up -d --build producer`.

- Ensure Firebolt Core is reachable:
  - Test: `curl -s http://localhost:3473 --data-binary 'SELECT 1'`
  - The sink and dashboard containers use `FIREBOLT_CORE_URL=http://host.docker.internal:3473` to reach Core from inside Docker.

- Ensure Kafka is healthy:
  - `docker compose ps` should show `kafka` healthy.
  - List topics: `docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list`

### 6) Tear down

```bash
docker compose down -v
# Optionally stop Firebolt Core
docker rm -f firebolt-core
```

### Project structure

- `docker-compose.yml` – services: `kafka`, `producer`, `sink`, `dashboard`
- `env.example` – template for runtime configuration (copy to `.env`)
- `firebolt/init.sh` – creates `demo_db` and `demo_events`
- `apps/producer` – Python Kafka producer
- `apps/sink` – Python consumer that inserts into Firebolt Core via HTTP
- `apps/dashboard` – FastAPI dashboard with live metrics
