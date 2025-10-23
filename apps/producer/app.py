import os
import time
import random
import socket
import orjson
from kafka import KafkaProducer

bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
topic = os.getenv("TOPIC", "demo.events")
events_per_second = float(os.getenv("EVENTS_PER_SECOND", "2"))

producer = None
for attempt in range(60):
    try:
        producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers.split(","),
            value_serializer=lambda v: orjson.dumps(v),
            linger_ms=50,
        )
        break
    except Exception as e:
        time.sleep(1)

if producer is None:
    raise RuntimeError("Failed to connect to Kafka after retries")

hostname = socket.gethostname()

event_types = ["click", "view", "purchase", "login"]

def generate_event(event_id: int):
    return {
        "event_id": event_id,
        "user_id": random.randint(1, 1000),
        "event_type": random.choice(event_types),
        "event_ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "payload": {"source": hostname, "value": random.random()},
    }

interval = 1.0 / max(events_per_second, 0.1)

event_id = 1
sent = 0
while True:
    evt = generate_event(event_id)
    try:
        producer.send(topic, value=evt)
        sent += 1
        if sent % 10 == 0:
            print(f"producer sent {sent} events to {topic}", flush=True)
    except Exception as e:
        print(f"producer error: {e}", flush=True)
        time.sleep(1)
        continue
    event_id += 1
    time.sleep(interval)
