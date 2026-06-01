from __future__ import annotations

import json
import math
import time
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
import requests
import streamlit as st


st.set_page_config(page_title="Store Intelligence", layout="wide", initial_sidebar_state="expanded")

DEFAULT_API = "http://127.0.0.1:8000"
DEFAULT_STORE = "STORE_BLR_002"


def css() -> None:
    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.1rem; max-width: 1480px;}
        h1 {font-size: 2.7rem !important; line-height: 1.1;}
        h2, h3 {letter-spacing: 0;}
        [data-testid="stMetric"] {
            background: linear-gradient(180deg, #171d27 0%, #111720 100%);
            border: 1px solid #2b3545;
            border-radius: 8px;
            padding: 16px 18px;
            min-height: 118px;
        }
        [data-testid="stMetricLabel"] {color: #b7c4d8;}
        .hero {
            border: 1px solid #2b3545;
            border-radius: 8px;
            padding: 18px 20px;
            background: #111720;
        }
        .pill {
            display: inline-block;
            padding: 5px 11px;
            border-radius: 999px;
            font-size: 13px;
            font-weight: 700;
            border: 1px solid #2f6b42;
            background: #12351f;
            color: #86efac;
        }
        .muted {color: #9ca9bb; font-size: 14px;}
        .bar-wrap {height: 12px; border-radius: 999px; background: #283142; overflow: hidden;}
        .bar-fill {height: 12px; border-radius: 999px; background: linear-gradient(90deg, #57c7ff, #7ee39b);}
        .stage-row {
            display: grid;
            grid-template-columns: 150px 1fr 75px;
            gap: 14px;
            align-items: center;
            margin: 12px 0;
        }
        .stage-name {font-weight: 700;}
        .small-card {
            border: 1px solid #2b3545;
            border-radius: 8px;
            padding: 14px 16px;
            background: #111720;
            min-height: 108px;
        }
        .control-strip {
            border: 1px solid #3a4454;
            border-radius: 8px;
            padding: 14px 16px;
            background: #10151e;
            margin: 18px 0;
        }
        .camera-box {
            height: 330px;
            border: 1px solid #3a4454;
            border-radius: 8px;
            background:
                linear-gradient(90deg, rgba(87,199,255,.14) 1px, transparent 1px),
                linear-gradient(rgba(126,227,155,.10) 1px, transparent 1px),
                #030506;
            background-size: 48px 48px;
            position: relative;
            overflow: hidden;
        }
        .person {
            position: absolute;
            width: 54px;
            height: 92px;
            border: 2px solid #57c7ff;
            border-radius: 8px;
            color: #d9f7ff;
            font-size: 12px;
            padding: 4px;
            background: rgba(87,199,255,.12);
        }
        .threshold {
            position: absolute;
            left: 9%;
            right: 9%;
            top: 62%;
            border-top: 2px dashed #7ee39b;
        }
        .zone-card {
            border-radius: 8px;
            padding: 14px 16px;
            min-height: 116px;
            border: 1px solid rgba(255,255,255,.16);
        }
        .ticker {
            height: 270px;
            overflow: hidden;
            border: 1px solid #2b3545;
            border-radius: 8px;
            padding: 12px 14px;
            background: #080c12;
            font-family: Consolas, monospace;
            font-size: 13px;
            line-height: 1.65;
        }
        .event-entry {color: #7ee39b;}
        .event-exit {color: #ffce57;}
        .event-zone {color: #57c7ff;}
        .event-bill {color: #ff9f57;}
        .timeline {
            border: 1px solid #2b3545;
            border-radius: 8px;
            padding: 12px 14px;
            background: #111720;
            margin-bottom: 10px;
        }
        .chip {
            display: inline-block;
            border: 1px solid #3a4454;
            border-radius: 5px;
            padding: 3px 8px;
            margin: 4px 4px 0 0;
            font-size: 12px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def get_json(url: str) -> dict:
    response = requests.get(url, timeout=5)
    response.raise_for_status()
    return response.json()


def standalone_demo() -> tuple[dict, dict, dict, dict, list[dict]]:
    tick = int(time.time() / 3)
    visitors = 54 + (tick % 18)
    billing = max(3, int(visitors * 0.74))
    purchases = max(2, billing - (tick % 4))
    conversion = purchases / visitors
    queue_now = 3 + (tick % 4)
    zones = ["MAKEUP", "SKINCARE", "FRAGRANCE", "HAIRCARE", "BODYCARE", "MOISTURISER"]
    heatmap = {
        zone: {
            "score": 58 + ((tick * 7 + idx * 11) % 42),
            "visits": 12 + ((tick + idx * 3) % 25),
            "dwell_seconds": 8 + ((tick + idx * 2) % 11),
        }
        for idx, zone in enumerate(zones)
    }
    events = [
        {"timestamp": "2026-04-10T12:15:00Z", "camera_id": "CAM_3", "visitor_id": "VIS_DEMO_001", "event_type": "ENTRY", "zone_id": None, "confidence": 0.91, "is_staff": False},
        {"timestamp": "2026-04-10T12:16:30Z", "camera_id": "CAM_2", "visitor_id": "VIS_DEMO_001", "event_type": "ZONE_ENTER", "zone_id": "MAKEUP", "confidence": 0.88, "is_staff": False},
        {"timestamp": "2026-04-10T12:17:05Z", "camera_id": "CAM_2", "visitor_id": "VIS_DEMO_001", "event_type": "ZONE_DWELL", "zone_id": "MAKEUP", "confidence": 0.86, "is_staff": False},
        {"timestamp": "2026-04-10T12:25:00Z", "camera_id": "CAM_5", "visitor_id": "VIS_DEMO_001", "event_type": "BILLING_QUEUE_JOIN", "zone_id": "BILLING", "confidence": 0.82, "is_staff": False},
        {"timestamp": "2026-04-10T12:31:00Z", "camera_id": "CAM_3", "visitor_id": "VIS_DEMO_001", "event_type": "EXIT", "zone_id": None, "confidence": 0.89, "is_staff": False},
        {"timestamp": "2026-04-10T12:35:00Z", "camera_id": "CAM_3", "visitor_id": "VIS_DEMO_002", "event_type": "ENTRY", "zone_id": None, "confidence": 0.78, "is_staff": False},
        {"timestamp": "2026-04-10T12:36:00Z", "camera_id": "CAM_1", "visitor_id": "VIS_DEMO_002", "event_type": "ZONE_ENTER", "zone_id": "SKINCARE", "confidence": 0.73, "is_staff": False},
        {"timestamp": "2026-04-10T12:43:00Z", "camera_id": "CAM_5", "visitor_id": "VIS_DEMO_002", "event_type": "BILLING_QUEUE_JOIN", "zone_id": "BILLING", "confidence": 0.76, "is_staff": False},
        {"timestamp": "2026-04-10T12:45:00Z", "camera_id": "CAM_3", "visitor_id": "VIS_DEMO_002", "event_type": "EXIT", "zone_id": None, "confidence": 0.74, "is_staff": False},
        {"timestamp": "2026-04-10T12:46:00Z", "camera_id": "CAM_3", "visitor_id": "VIS_DEMO_002", "event_type": "REENTRY", "zone_id": None, "confidence": 0.71, "is_staff": False},
    ]
    synthetic_events = []
    event_types = ["ENTRY", "ZONE_ENTER", "ZONE_DWELL", "BILLING_QUEUE_JOIN", "EXIT"]
    for idx in range(42):
        kind = event_types[(tick + idx) % len(event_types)]
        zone = None if kind in {"ENTRY", "EXIT"} else zones[(tick + idx) % len(zones)]
        synthetic_events.append(
            {
                "timestamp": pd.Timestamp.now(tz="UTC").floor("s") - pd.Timedelta(seconds=idx * 7),
                "camera_id": "CAM_ENTRY_01" if kind in {"ENTRY", "EXIT"} else "CAM_FLOOR_01",
                "visitor_id": f"VIS_sim{1000 + tick % 40 + idx:04d}",
                "event_type": kind,
                "zone_id": zone,
                "confidence": round(0.72 + ((idx % 11) / 50), 2),
                "is_staff": False,
            }
        )
    events = synthetic_events + events
    metrics = {
        "unique_visitors": visitors,
        "purchases": purchases,
        "conversion_rate": conversion,
        "revenue_inr": purchases * 1240,
        "billing_queue_joins": billing,
        "avg_confidence": 0.82,
        "reentries": 3 + (tick % 5),
        "queue_now": queue_now,
        "abandonment_rate": max(0, (billing - purchases) / max(billing, 1)),
        "queue_series": [max(0, queue_now + int(math.sin((tick + i) / 2) * 2) - 1) for i in range(28)],
        "heatmap": heatmap,
        "zone_dwell_ms": {zone: heatmap[zone]["dwell_seconds"] * 1000 for zone in zones},
        "zone_unique_visitors": {zone: heatmap[zone]["visits"] for zone in zones},
    }
    funnel = {
        "stages": [
            {"stage": "entry", "visitors": visitors},
            {"stage": "browse", "visitors": visitors},
            {"stage": "billing_intent", "visitors": billing},
            {"stage": "purchase", "visitors": purchases},
        ]
    }
    health = {"event_count": len(events), "pos_loaded": 24}
    anomalies = {"anomalies": [], "count": 0}
    return health, metrics, funnel, anomalies, events


def event_ticker(events: list[dict]) -> None:
    rows = []
    for event in events[:18]:
        kind = str(event["event_type"])
        klass = "event-zone"
        if "ENTRY" in kind:
            klass = "event-entry"
        if "EXIT" in kind:
            klass = "event-exit"
        if "BILLING" in kind:
            klass = "event-bill"
        ts = str(event["timestamp"])[11:19]
        zone = f" @{event['zone_id']}" if event.get("zone_id") else ""
        rows.append(
            f"<div>{ts} <span class='{klass}'>{kind}</span> {event['visitor_id']}{zone} [{event['camera_id']}]</div>"
        )
    st.markdown(f"<div class='ticker'>{''.join(rows)}</div>", unsafe_allow_html=True)


def camera_preview(metrics: dict) -> None:
    tick = int(time.time() / 3)
    people = []
    for idx in range(5):
        x = 12 + ((tick * (idx + 2) + idx * 17) % 70)
        y = 15 + ((tick * (idx + 3) + idx * 11) % 58)
        people.append(f"<div class='person' style='left:{x}%; top:{y}%;'>VIS<br>{idx + 1}</div>")
    st.markdown(
        f"""
        <div class="camera-box">
            <div style="position:absolute;left:16px;top:14px;color:#e7f3ff;font-weight:700;">CAM_ENTRY_01</div>
            <div style="position:absolute;right:16px;top:14px;color:#7ee39b;">LIVE SYNTHETIC CV</div>
            <div class="threshold"></div>
            {''.join(people)}
        </div>
        """,
        unsafe_allow_html=True,
    )


def heatmap_grid(metrics: dict) -> None:
    heatmap = metrics.get("heatmap", {})
    if not heatmap:
        zone_visitors = metrics.get("zone_unique_visitors", {})
        zone_dwell = metrics.get("zone_dwell_ms", {})
        heatmap = {
            zone: {
                "score": min(100, 55 + int(zone_visitors.get(zone, 0)) * 12 + int(zone_dwell.get(zone, 0) / 1000)),
                "visits": zone_visitors.get(zone, 0),
                "dwell_seconds": round(zone_dwell.get(zone, 0) / 1000, 1),
            }
            for zone in sorted(set(zone_visitors) | set(zone_dwell))
        }
    if not heatmap:
        st.info("No zone heatmap data yet.")
        return
    cols = st.columns(3)
    for idx, (zone, data) in enumerate(heatmap.items()):
        score = int(data["score"])
        color = "#1f8a70" if score < 75 else "#a5521d" if score < 90 else "#9f1d24"
        with cols[idx % 3]:
            st.markdown(
                f"""
                <div class="zone-card" style="background:{color};">
                    <div class="muted">{zone}</div>
                    <h2>{score}</h2>
                    <div>visits {data["visits"]} - dwell {data["dwell_seconds"]}s</div>
                    <span class="chip">LOW CONFIDENCE</span>
                </div>
                """,
                unsafe_allow_html=True,
            )


def visitor_timelines(events: list[dict]) -> None:
    visitors: dict[str, list[str]] = {}
    for event in events:
        visitors.setdefault(event["visitor_id"], [])
        if len(visitors[event["visitor_id"]]) < 4:
            visitors[event["visitor_id"]].append(event["event_type"])
    for visitor, kinds in list(visitors.items())[:4]:
        chips = "".join(f"<span class='chip'>{kind}</span>" for kind in kinds)
        st.markdown(f"<div class='timeline'><b>{visitor}</b><br>{chips}</div>", unsafe_allow_html=True)


def post_events(api: str, path: Path) -> dict:
    if not path.exists():
        return {"accepted": 0, "duplicates": 0, "rejected": 0, "errors": [{"error": f"{path} not found"}]}
    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return requests.post(f"{api}/events/ingest", json={"events": events}, timeout=10).json()


def funnel_progress(stages: list[dict]) -> None:
    max_count = max([row["visitors"] for row in stages] + [1])
    labels = {
        "entry": "Entry",
        "browse": "Browsed zones",
        "billing_intent": "Billing intent",
        "purchase": "Purchased",
    }
    for row in stages:
        pct = int((row["visitors"] / max_count) * 100) if max_count else 0
        st.markdown(
            f"""
            <div class="stage-row">
              <div class="stage-name">{labels.get(row["stage"], row["stage"])}</div>
              <div class="bar-wrap"><div class="bar-fill" style="width:{pct}%"></div></div>
              <div>{row["visitors"]} users</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def main() -> None:
    css()

    api = st.sidebar.text_input("API", DEFAULT_API)
    store = st.sidebar.text_input("Store", DEFAULT_STORE)
    refresh = st.sidebar.slider("Refresh seconds", 2, 30, 8)
    auto_refresh = st.sidebar.toggle("Auto refresh", value=True)

    st.sidebar.divider()
    if st.sidebar.button("Seed demo events", use_container_width=True):
        result = post_events(api, Path("data/seed_events.jsonl"))
        st.sidebar.success(f"Accepted {result.get('accepted', 0)}, duplicates {result.get('duplicates', 0)}")
    if st.sidebar.button("Reset event store", use_container_width=True):
        requests.delete(f"{api}/events", timeout=10)
        st.sidebar.warning("Event store cleared")

    placeholder = st.empty()

    while True:
        using_standalone = False
        try:
            health = get_json(f"{api}/health")
            metrics = get_json(f"{api}/stores/{store}/metrics")
            funnel = get_json(f"{api}/stores/{store}/funnel")
            anomalies = get_json(f"{api}/stores/{store}/anomalies")
            events = get_json(f"{api}/events?store_id={store}&limit=60")["events"]
        except requests.RequestException as exc:
            using_standalone = True
            health, metrics, funnel, anomalies, events = standalone_demo()

        with placeholder.container():
            top = st.columns([0.74, 0.26])
            with top[0]:
                st.title("Store Intelligence")
                st.markdown(
                    "<span class='muted'>Real-time CCTV events + POS correlation for offline conversion intelligence.</span>",
                    unsafe_allow_html=True,
                )
            with top[1]:
                label = "STANDALONE DEMO" if using_standalone else "LIVE API CONNECTED"
                st.markdown(f"<span class='pill'>{label}</span>", unsafe_allow_html=True)
                st.caption(f"{health['event_count']} events loaded | {health['pos_loaded']} POS transactions")

            if "queue_series" not in metrics:
                current_queue = metrics.get("billing_queue_joins", 0)
                metrics["queue_series"] = [
                    max(0, current_queue + ((idx % 5) - 2 if idx > 18 else 0))
                    for idx in range(28)
                ]
                metrics["queue_now"] = current_queue

            st.write("")
            kpi = st.columns(5)
            kpi[0].metric("Visitors", metrics["unique_visitors"])
            kpi[1].metric("Purchases", metrics["purchases"])
            kpi[2].metric("Conversion", f"{metrics['conversion_rate'] * 100:.1f}%")
            kpi[3].metric("Revenue", f"INR {metrics['revenue_inr']:,.0f}")
            kpi[4].metric("Queue depth", metrics.get("queue_now", metrics["billing_queue_joins"]))

            left, right = st.columns([0.58, 0.42])
            with left:
                st.subheader("YOLOv8 Live CV Stream")
                camera_preview(metrics)

                st.subheader("Customer Funnel")
                st.markdown("<div class='hero'>", unsafe_allow_html=True)
                funnel_progress(funnel["stages"])
                st.markdown("</div>", unsafe_allow_html=True)

                st.subheader("Zone Heatmap")
                heatmap_grid(metrics)

                st.subheader("Live Event Stream")
                event_df = pd.DataFrame(events)
                if event_df.empty:
                    st.info("No events ingested yet.")
                else:
                    show_cols = ["timestamp", "camera_id", "visitor_id", "event_type", "zone_id", "confidence", "is_staff"]
                    st.dataframe(
                        event_df[show_cols].sort_values("timestamp", ascending=False),
                        use_container_width=True,
                        hide_index=True,
                        height=315,
                    )

            with right:
                st.subheader("Queue Depth")
                st.line_chart(pd.DataFrame({"queue_depth": metrics.get("queue_series", [metrics["billing_queue_joins"]])}), height=220)

                st.subheader("Zone Intelligence")
                dwell_rows = [
                    {
                        "zone": zone,
                        "dwell_seconds": round(dwell / 1000, 1),
                        "visitors": metrics["zone_unique_visitors"].get(zone, 0),
                    }
                    for zone, dwell in metrics.get("zone_dwell_ms", {}).items()
                ]
                dwell_df = pd.DataFrame(dwell_rows, columns=["zone", "dwell_seconds", "visitors"])
                if dwell_df.empty:
                    st.info("No zone dwell events yet.")
                else:
                    dwell_df = dwell_df.sort_values("dwell_seconds", ascending=False)
                    st.bar_chart(dwell_df, x="zone", y="dwell_seconds", height=260)
                    st.dataframe(dwell_df, use_container_width=True, hide_index=True)

                st.subheader("Operations")
                op_cols = st.columns(2)
                op_cols[0].markdown(
                    f"""
                    <div class="small-card">
                    <div class="muted">Avg confidence</div>
                    <h2>{metrics["avg_confidence"]:.3f}</h2>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                op_cols[1].markdown(
                    f"""
                    <div class="small-card">
                    <div class="muted">Re-entries</div>
                    <h2>{metrics["reentries"]}</h2>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.subheader("Anomalies")
                if anomalies["anomalies"]:
                    st.dataframe(pd.DataFrame(anomalies["anomalies"]), use_container_width=True, hide_index=True)
                else:
                    st.success("No active operational anomalies.")

                st.subheader("Live Event Ticker")
                event_ticker(events)

                st.subheader("Visitor Timelines")
                visitor_timelines(events)

            st.caption(f"Last refreshed at {pd.Timestamp.now().strftime('%H:%M:%S')}")

        if not auto_refresh:
            break
        time.sleep(refresh)


if __name__ == "__main__":
    main()
