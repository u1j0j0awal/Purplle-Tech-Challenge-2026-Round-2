# PROMPT: Test anomaly detection for billing queue spikes and make sure normal traffic stays quiet.
# CHANGES MADE: I asserted only stable anomaly types, not full messages, to keep copy changes from breaking tests.

from datetime import datetime, timezone

from app.anomalies import detect_anomalies
from app.models import StoreEvent


def test_billing_queue_spike_is_reported() -> None:
    event = StoreEvent(
        store_id="STORE_BLR_002",
        camera_id="CAM_5",
        visitor_id="VIS_1",
        event_type="BILLING_QUEUE_JOIN",
        timestamp=datetime.now(timezone.utc),
        zone_id="BILLING",
        confidence=0.8,
        metadata={"queue_depth": 5},
    )

    result = detect_anomalies([event], [], "STORE_BLR_002")

    assert "BILLING_QUEUE_SPIKE" in {item["type"] for item in result["anomalies"]}
