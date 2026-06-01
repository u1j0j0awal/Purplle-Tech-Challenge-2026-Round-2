# Store Intelligence System

AI-powered retail analytics from raw CCTV footage. The system emits structured visitor events, ingests them through a production-aware FastAPI service, correlates POS transactions, and exposes store metrics, funnel, heatmap and anomaly endpoints.

## Quick Start

```bash
docker compose up --build
```

Open:

- API health: `http://localhost:8000/health`
- Acceptance metric alias: `http://localhost:8000/metrics`
- Store metrics: `http://localhost:8000/stores/STORE_BLR_002/metrics`
- Funnel: `http://localhost:8000/stores/STORE_BLR_002/funnel`
- Anomalies: `http://localhost:8000/stores/STORE_BLR_002/anomalies`

## Generate Events

Do not commit raw videos or challenge datasets. Keep them beside this repo, then run:

```bash
python -m pipeline.detect --video-dir "../CCTV Footage" --out data/events.jsonl --stride 15
```

For a fast acceptance-gate smoke test without clips:

```bash
python -m pipeline.detect --demo --out data/events.jsonl
```

Ingest generated events into the running API:

```bash
python - <<'PY'
import json, requests
events=[json.loads(line) for line in open("data/events.jsonl", encoding="utf-8")]
print(requests.post("http://localhost:8000/events/ingest", json={"events": events[:500]}).json())
PY
```

## POS Preparation

The provided item-level CSV can be converted to compact POS transactions:

```bash
python scripts/prepare_pos.py "../Brigade_Bangalore_10_April_26 (1)bc6219c.csv" --out data/pos_transactions.csv
```

`data/*.csv`, `data/*.jsonl` and videos are gitignored.

## Dashboard

With the API running:

```bash
streamlit run dashboard/app.py
```

The dashboard auto-refreshes visitors, purchases, conversion rate, revenue, dwell and anomalies.

## Tests

```bash
pytest --cov=app --cov=pipeline
```

## Streamlit Cloud

`requirements.txt` is intentionally lightweight for Streamlit Community Cloud. The full API/CV dependency set lives in `requirements-api.txt` and is used by Docker.

## Repository Layout

- `pipeline/`: YOLO person detection, lightweight tracking, zone/event emission.
- `app/`: FastAPI ingestion, idempotent event store, metrics, funnel, anomalies.
- `dashboard/`: Streamlit live dashboard.
- `tests/`: edge-case tests with required AI prompt headers.
- `DESIGN.md`, `CHOICES.md`: architecture and trade-off reasoning.
