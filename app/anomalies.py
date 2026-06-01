from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

from app.metrics import compute_metrics
from app.models import EventType, StoreEvent
from app.pos import Purchase


def detect_anomalies(events: list[StoreEvent], purchases: list[Purchase], store_id: str) -> dict:
    metrics = compute_metrics(events, purchases, store_id)
    store_events = [e for e in events if e.store_id == store_id]
    latest_event_ts = max((e.timestamp for e in store_events), default=datetime.now(timezone.utc))
    recent = [e for e in store_events if e.timestamp >= latest_event_ts - timedelta(minutes=10)]
    warnings: list[dict] = []

    queue_depths = [
        int(e.metadata.get("queue_depth", 0))
        for e in events
        if e.store_id == store_id and e.event_type == EventType.BILLING_QUEUE_JOIN
    ]
    if queue_depths and max(queue_depths) >= 4:
        warnings.append(
            {
                "type": "BILLING_QUEUE_SPIKE",
                "severity": "high",
                "message": f"Observed queue depth {max(queue_depths)}; add billing support.",
            }
        )

    if metrics["unique_visitors"] >= 5 and metrics["conversion_rate"] < 0.15:
        warnings.append(
            {
                "type": "CONVERSION_DROP",
                "severity": "medium",
                "message": "Visitor volume is present but POS-correlated conversion is low.",
            }
        )

    counts_by_camera = Counter(e.camera_id for e in store_events)
    for camera_id, count in counts_by_camera.items():
        camera_recent = [e for e in recent if e.camera_id == camera_id]
        if count >= 3 and not camera_recent:
            warnings.append(
                {
                    "type": "STALE_FEED",
                    "severity": "low",
                    "camera_id": camera_id,
                    "message": "No events from this camera in the latest 10-minute event-time window.",
                }
            )

    return {"store_id": store_id, "anomalies": warnings, "count": len(warnings)}
