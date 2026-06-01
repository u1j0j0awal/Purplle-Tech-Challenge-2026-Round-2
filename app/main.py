from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.anomalies import detect_anomalies
from app.funnel import compute_funnel
from app.metrics import compute_metrics
from app.models import IngestError, IngestResponse, StoreEvent
from app.pos import load_pos
from app.storage import EventStore

STORE_ID = "STORE_BLR_002"

app = FastAPI(title="Store Intelligence API", version="1.0.0")
store = EventStore()


@app.get("/health")
def health() -> dict[str, Any]:
    events = store.all()
    return {
        "status": "ok",
        "event_count": len(events),
        "event_path": str(store.path),
        "pos_loaded": len(load_pos()),
    }


@app.post("/events/ingest", response_model=IngestResponse)
async def ingest(request: Request) -> IngestResponse:
    payload = await request.json()
    raw_events = payload.get("events", payload if isinstance(payload, list) else [])
    accepted_events: list[StoreEvent] = []
    errors: list[IngestError] = []
    for index, raw in enumerate(raw_events[:500]):
        try:
            accepted_events.append(StoreEvent.model_validate(raw))
        except ValidationError as exc:
            errors.append(IngestError(index=index, error=exc.errors()[0]["msg"]))
    accepted, duplicates = store.add_many(accepted_events)
    return IngestResponse(
        accepted=accepted,
        duplicates=duplicates,
        rejected=len(errors),
        errors=errors,
    )


@app.get("/events")
def events(limit: int = 100, store_id: str | None = None) -> dict:
    rows = store.all()
    if store_id:
        rows = [event for event in rows if event.store_id == store_id]
    rows = rows[-max(1, min(limit, 500)) :]
    return {
        "count": len(rows),
        "events": [event.model_dump(mode="json") for event in rows],
    }


@app.get("/stores/{store_id}/metrics")
def metrics(store_id: str) -> dict:
    return compute_metrics(store.all(), load_pos(), store_id)


@app.get("/metrics")
@app.get("/Metrics")
def metrics_alias() -> dict:
    return metrics(os.getenv("STORE_INTEL_DEFAULT_STORE", STORE_ID))


@app.get("/stores/{store_id}/funnel")
def funnel(store_id: str) -> dict:
    return compute_funnel(store.all(), load_pos(), store_id)


@app.get("/stores/{store_id}/anomalies")
def anomalies(store_id: str) -> dict:
    return detect_anomalies(store.all(), load_pos(), store_id)


@app.get("/stores/{store_id}/heatmap")
def heatmap(store_id: str) -> dict:
    metric = compute_metrics(store.all(), load_pos(), store_id)
    return {
        "store_id": store_id,
        "zones": [
            {
                "zone_id": zone_id,
                "dwell_ms": dwell,
                "unique_visitors": metric["zone_unique_visitors"].get(zone_id, 0),
            }
            for zone_id, dwell in metric["zone_dwell_ms"].items()
        ],
    }


@app.delete("/events")
def clear_events() -> JSONResponse:
    store.clear()
    return JSONResponse({"status": "cleared"})
