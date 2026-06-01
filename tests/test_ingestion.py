# PROMPT: Create API tests for idempotent event ingestion and the metrics acceptance-gate endpoint.
# CHANGES MADE: The test uses a temporary EventStore to avoid depending on local generated files.

from datetime import datetime, timezone

from fastapi.testclient import TestClient

import app.main as main
from app.storage import EventStore


def test_ingest_is_idempotent(tmp_path) -> None:
    main.store = EventStore(str(tmp_path / "events.jsonl"))
    client = TestClient(main.app)
    payload = {
        "events": [
            {
                "event_id": "evt-1",
                "store_id": "STORE_BLR_002",
                "camera_id": "CAM_3",
                "visitor_id": "VIS_1",
                "event_type": "ENTRY",
                "timestamp": datetime(2026, 4, 10, 12, tzinfo=timezone.utc).isoformat(),
                "zone_id": None,
                "dwell_ms": 0,
                "is_staff": False,
                "confidence": 0.9,
                "metadata": {},
            }
        ]
    }

    first = client.post("/events/ingest", json=payload)
    second = client.post("/events/ingest", json=payload)

    assert first.status_code == 200
    assert first.json()["accepted"] == 1
    assert second.json()["duplicates"] == 1
    assert client.get("/metrics").status_code == 200
