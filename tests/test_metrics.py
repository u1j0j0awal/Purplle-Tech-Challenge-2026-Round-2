# PROMPT: Build tests for the Store Intelligence metric logic, including conversion, re-entry and zero-traffic behavior.
# CHANGES MADE: I kept the fixtures tiny and explicit so failures explain the business rule rather than snapshot noise.

from datetime import datetime, timezone

from app.metrics import compute_metrics
from app.models import StoreEvent
from app.pos import Purchase


def event(visitor: str, kind: str, ts: str, zone: str | None = None, dwell: int = 0) -> StoreEvent:
    return StoreEvent(
        store_id="STORE_BLR_002",
        camera_id="CAM_3",
        visitor_id=visitor,
        event_type=kind,
        timestamp=datetime.fromisoformat(ts).replace(tzinfo=timezone.utc),
        zone_id=zone,
        dwell_ms=dwell,
        confidence=0.9,
    )


def test_metrics_correlates_purchase_to_session() -> None:
    events = [
        event("VIS_1", "ENTRY", "2026-04-10T12:00:00"),
        event("VIS_1", "ZONE_ENTER", "2026-04-10T12:04:00", "MAKEUP"),
        event("VIS_1", "BILLING_QUEUE_JOIN", "2026-04-10T12:12:00", "BILLING"),
        event("VIS_1", "EXIT", "2026-04-10T12:20:00"),
    ]
    purchases = [Purchase("TXN_1", datetime(2026, 4, 10, 12, 18, tzinfo=timezone.utc), 999.0)]

    metrics = compute_metrics(events, purchases, "STORE_BLR_002")

    assert metrics["unique_visitors"] == 1
    assert metrics["purchases"] == 1
    assert metrics["conversion_rate"] == 1.0
    assert metrics["billing_queue_joins"] == 1


def test_staff_and_empty_store_do_not_break_metrics() -> None:
    staff = event("STAFF_1", "ENTRY", "2026-04-10T12:00:00")
    staff.is_staff = True

    assert compute_metrics([], [], "STORE_BLR_002")["conversion_rate"] == 0.0
    assert compute_metrics([staff], [], "STORE_BLR_002")["unique_visitors"] == 0
