import os
import time
import re
import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from kafka import KafkaConsumer, TopicPartition

app = FastAPI()

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
TOPIC = os.getenv("TOPIC", "demo.events")
FIREBOLT_CORE_URL = os.getenv("FIREBOLT_CORE_URL", "http://host.docker.internal:3473")
FIREBOLT_DB = os.getenv("FIREBOLT_DB", "demo_db")

_last_metrics = {"ts": 0, "data": {"produced": 0, "ingested": 0}}


def get_kafka_count_fast() -> int:
    try:
        consumer = KafkaConsumer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS.split(","))
        partitions = consumer.partitions_for_topic(TOPIC)
        if not partitions:
            return 0
        tps = [TopicPartition(TOPIC, p) for p in partitions]
        # beginning_offsets/end_offsets accept a list of TopicPartition
        beg = consumer.beginning_offsets(tps)
        end = consumer.end_offsets(tps)
        return sum(max(0, end.get(tp, 0) - beg.get(tp, 0)) for tp in tps)
    except Exception:
        return -1


def get_firebolt_count() -> int:
    try:
        url = f"{FIREBOLT_CORE_URL}?database={FIREBOLT_DB}"
        r = requests.post(url, data=b"SELECT COUNT(*) FROM demo_events;", timeout=3)
        r.raise_for_status()
        # extract last integer in response
        m = re.findall(r"\b\d+\b", r.text)
        return int(m[-1]) if m else -1
    except Exception:
        return -1


@app.get("/", response_class=HTMLResponse)
async def index():
    return """
<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <title>Kafka → Firebolt Core Dashboard</title>
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 24px; }
    .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; }
    .card { border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; box-shadow: 0 1px 2px rgba(0,0,0,.05); }
    .kpi { font-size: 28px; font-weight: 700; }
    .label { color: #6b7280; font-size: 12px; text-transform: uppercase; letter-spacing: .05em; }
    .flow { margin-top: 20px; }
    .box { display:inline-block; padding:10px 14px; border:1px solid #e5e7eb; border-radius:6px; }
    .arrow { display:inline-block; padding:0 8px; color:#6b7280; }
    .muted { color:#6b7280; font-size:12px; }
  </style>
</head>
<body>
  <h2>Kafka → Firebolt Core Demo Dashboard</h2>
  <div class=\"flow\">
    <span class=\"box\">Producer</span>
    <span class=\"arrow\">➡</span>
    <span class=\"box\">Kafka (topic: <code>demo.events</code>)</span>
    <span class=\"arrow\">➡</span>
    <span class=\"box\">Sink</span>
    <span class=\"arrow\">➡</span>
    <span class=\"box\">Firebolt Core (table: <code>demo_events</code>)</span>
  </div>

  <div class=\"cards\" style=\"margin-top:20px;\">
    <div class=\"card\">
      <div class=\"label\">Kafka messages produced</div>
      <div id=\"produced\" class=\"kpi\">…</div>
      <div class=\"muted\">Computed via offsets</div>
    </div>
    <div class=\"card\">
      <div class=\"label\">Rows ingested in Firebolt</div>
      <div id=\"ingested\" class=\"kpi\">…</div>
      <div class=\"muted\">SELECT COUNT(*) FROM demo_events</div>
    </div>
  </div>

  <script>
    async function refresh(){
      try{
        const r = await fetch('/metrics');
        const m = await r.json();
        document.getElementById('produced').textContent = m.produced >= 0 ? m.produced : 'N/A';
        document.getElementById('ingested').textContent = m.ingested >= 0 ? m.ingested : 'N/A';
      }catch(e){ /* ignore */ }
    }
    refresh();
    setInterval(refresh, 2000);
  </script>
</body>
</html>
"""


@app.get("/metrics", response_class=JSONResponse)
async def metrics():
    now = time.time()
    if now - _last_metrics["ts"] > 1.0:
        produced = get_kafka_count_fast()
        ingested = get_firebolt_count()
        _last_metrics["ts"] = now
        _last_metrics["data"] = {"produced": produced, "ingested": ingested}
    return _last_metrics["data"]
