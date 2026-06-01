from __future__ import annotations

from app.metrics import correlate_purchases, session_summary
from app.models import StoreEvent
from app.pos import Purchase


def compute_funnel(events: list[StoreEvent], purchases: list[Purchase], store_id: str) -> dict:
    sessions = session_summary(events, store_id)
    matches = correlate_purchases(sessions, purchases)
    entered = [s for s in sessions.values() if s["entered"]]
    browsed = [s for s in entered if s["zones"] - {"ENTRY_THRESHOLD"}]
    billing = [s for s in entered if s["billing_joined"] or "BILLING" in s["zones"]]
    purchased = [s for s in entered if s["visitor_id"] in matches]

    stages = [
        ("entry", len(entered)),
        ("browse", len(browsed)),
        ("billing_intent", len(billing)),
        ("purchase", len(purchased)),
    ]
    result = []
    previous = stages[0][1] if stages else 0
    for name, count in stages:
        result.append(
            {
                "stage": name,
                "visitors": count,
                "conversion_from_previous": round(count / previous, 4) if previous else 0.0,
                "dropoff_from_previous": round((previous - count) / previous, 4) if previous else 0.0,
            }
        )
        previous = count
    return {"store_id": store_id, "stages": result}
