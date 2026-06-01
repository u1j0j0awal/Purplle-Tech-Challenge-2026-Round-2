from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from app.models import EventType, StoreEvent
from app.pos import Purchase


def customer_events(events: list[StoreEvent], store_id: str) -> list[StoreEvent]:
    return [e for e in events if e.store_id == store_id and not e.is_staff]


def session_summary(events: list[StoreEvent], store_id: str) -> dict[str, dict]:
    sessions: dict[str, dict] = {}
    for event in customer_events(events, store_id):
        session = sessions.setdefault(
            event.visitor_id,
            {
                "visitor_id": event.visitor_id,
                "first_seen": event.timestamp,
                "last_seen": event.timestamp,
                "entered": False,
                "exited": False,
                "zones": set(),
                "billing_joined": False,
                "reentry": False,
                "dwell_ms": 0,
            },
        )
        session["first_seen"] = min(session["first_seen"], event.timestamp)
        session["last_seen"] = max(session["last_seen"], event.timestamp)
        session["entered"] = session["entered"] or event.event_type in {EventType.ENTRY, EventType.REENTRY}
        session["exited"] = session["exited"] or event.event_type == EventType.EXIT
        session["reentry"] = session["reentry"] or event.event_type == EventType.REENTRY
        session["billing_joined"] = session["billing_joined"] or event.event_type == EventType.BILLING_QUEUE_JOIN
        if event.zone_id:
            session["zones"].add(event.zone_id)
        session["dwell_ms"] += event.dwell_ms
    return sessions


def correlate_purchases(sessions: dict[str, dict], purchases: list[Purchase]) -> dict[str, Purchase]:
    unmatched = sorted(sessions.values(), key=lambda s: s["last_seen"])
    matches: dict[str, Purchase] = {}
    for purchase in purchases:
        candidates = [
            s for s in unmatched
            if s["visitor_id"] not in matches
            and s["first_seen"] - timedelta(minutes=10) <= purchase.timestamp <= s["last_seen"] + timedelta(minutes=45)
        ]
        if not candidates:
            continue
        chosen = min(candidates, key=lambda s: abs((purchase.timestamp - s["last_seen"]).total_seconds()))
        matches[chosen["visitor_id"]] = purchase
    return matches


def compute_metrics(events: list[StoreEvent], purchases: list[Purchase], store_id: str) -> dict:
    sessions = session_summary(events, store_id)
    visitors = [s for s in sessions.values() if s["entered"]]
    matches = correlate_purchases(sessions, purchases)
    zone_dwell = defaultdict(int)
    zone_visitors: dict[str, set[str]] = defaultdict(set)
    event_counts = Counter()
    confidence_sum = 0.0

    for event in customer_events(events, store_id):
        event_counts[event.event_type.value] += 1
        confidence_sum += event.confidence
        if event.zone_id:
            zone_dwell[event.zone_id] += event.dwell_ms
            zone_visitors[event.zone_id].add(event.visitor_id)

    unique_visitors = len(visitors)
    purchase_count = len(matches)
    total_revenue = sum(p.basket_value_inr for p in matches.values())
    return {
        "store_id": store_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "unique_visitors": unique_visitors,
        "purchases": purchase_count,
        "conversion_rate": round(purchase_count / unique_visitors, 4) if unique_visitors else 0.0,
        "revenue_inr": round(total_revenue, 2),
        "avg_basket_value_inr": round(total_revenue / purchase_count, 2) if purchase_count else 0.0,
        "entries": event_counts[EventType.ENTRY.value] + event_counts[EventType.REENTRY.value],
        "exits": event_counts[EventType.EXIT.value],
        "reentries": event_counts[EventType.REENTRY.value],
        "billing_queue_joins": event_counts[EventType.BILLING_QUEUE_JOIN.value],
        "avg_confidence": round(confidence_sum / max(sum(event_counts.values()), 1), 3),
        "zone_dwell_ms": dict(sorted(zone_dwell.items())),
        "zone_unique_visitors": {k: len(v) for k, v in sorted(zone_visitors.items())},
        "event_counts": dict(event_counts),
    }
