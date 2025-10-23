import os
import time
import orjson
import requests
from kafka import KafkaConsumer

bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
topic = os.getenv("TOPIC", "demo.events")
core_url_base = os.getenv("FIREBOLT_CORE_URL", "http://host.docker.internal:3473")
db = os.getenv("FIREBOLT_DB", "demo_db")
table = os.getenv("FIREBOLT_TABLE", "demo_events")

def run_sql(sql: str):
    url = f"{core_url_base}?database={db}"
    resp = requests.post(url, data=sql.encode("utf-8"), timeout=10)
    resp.raise_for_status()
    return resp.text

# Ensure DB/table exist (idempotent)
try:
    requests.post(core_url_base, data=f"CREATE DATABASE IF NOT EXISTS \"{db}\";".encode("utf-8"), timeout=10).raise_for_status()
    run_sql(
        f"CREATE TABLE IF NOT EXISTS \"{table}\" (\n"
        f"  event_id INT,\n"
        f"  user_id INT,\n"
        f"  event_type TEXT,\n"
        f"  event_ts TEXT,\n"
        f"  payload TEXT\n"
        f");"
    )
except Exception as e:
    print(f"sink init DDL error: {e}", flush=True)

# Probe connection
try:
    out = run_sql("SELECT 1;")
    print(f"sink connected to Firebolt Core: {out.strip()}", flush=True)
except Exception as e:
    print(f"sink cannot reach Firebolt Core: {e}", flush=True)

consumer = None
for _ in range(60):
    try:
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers.split(","),
            value_deserializer=lambda v: orjson.loads(v),
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            group_id="firebolt-sink-demo",
            consumer_timeout_ms=2000,
            request_timeout_ms=30000,
            session_timeout_ms=10000,
            max_poll_interval_ms=300000,
        )
        break
    except Exception as e:
        print(f"sink waiting for Kafka: {e}", flush=True)
        time.sleep(1)

if consumer is None:
    raise RuntimeError("Failed to connect to Kafka after retries")

consumed = 0
while True:
    try:
        for msg in consumer:
            evt = msg.value
            consumed += 1
            if consumed % 10 == 0:
                print(f"sink consumed {consumed} messages", flush=True)
            event_id = int(evt.get("event_id", 0))
            user_id = int(evt.get("user_id", 0))
            event_type = str(evt.get("event_type", ""))
            event_ts = str(evt.get("event_ts", ""))
            payload_json = orjson.dumps(evt.get("payload", evt)).decode("utf-8")
            event_type_sql = event_type.replace("'", "''")
            event_ts_sql = event_ts.replace("'", "''")
            payload_sql = payload_json.replace("'", "''")
            sql = (
                f"INSERT INTO \"{table}\" (event_id, user_id, event_type, event_ts, payload) VALUES ("
                f"{event_id}, {user_id}, '{event_type_sql}', '{event_ts_sql}', '{payload_sql}'"
                f");"
            )
            try:
                run_sql(sql)
            except Exception as e:
                print(f"sink insert error: {e}", flush=True)
                time.sleep(0.2)
                continue
        # small pause to avoid tight loop when timed out
        time.sleep(0.2)
    except Exception as e:
        print(f"sink loop error: {e}", flush=True)
        time.sleep(1)
        continue
