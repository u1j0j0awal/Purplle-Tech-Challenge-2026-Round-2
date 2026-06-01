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
        [data-testid="stSidebar"] {display: none;}
        [data-testid="collapsedControl"] {display: none;}
        [data-testid="stAppViewContainer"] > .main {margin-left: 0;}
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
        .sim-strip {
            border: 1px solid #3a4454;
            border-radius: 8px;
            padding: 14px 16px;
            background: #10151e;
            margin: 16px 0 20px 0;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
        }
        .sim-btn {
            display: inline-block;
            border: 1px solid #3a4454;
            border-radius: 6px;
            padding: 6px 11px;
            margin-left: 6px;
            background: #171d27;
        }
        .sim-btn-active {
            border-color: #1faa8a;
            background: #1f8a70;
        }
        .source-note {
            color: #b7c4d8;
            font-size: 13px;
            margin-top: 4px;
        }
        .topbar {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 18px;
            margin-bottom: 18px;
        }
        .brand {
            font-size: 32px;
            font-weight: 800;
            color: #f7f4ef;
            line-height: 1.05;
        }
        .subtitle {
            color: #c2b6a3;
            font-size: 16px;
            margin-top: 6px;
        }
        .status-top {
            color: #e9dfcf;
            font-size: 15px;
            text-align: right;
            padding-top: 4px;
        }
        .status-dot {
            display:inline-block;
            width:10px;
            height:10px;
            border-radius:999px;
            background:#28c7a2;
            margin-right:7px;
        }
        .store-select {
            display:inline-block;
            margin-left:16px;
            padding:8px 14px;
            border:1px solid #6b6257;
            border-radius:5px;
            background:#12161f;
            color:#f7f4ef;
        }
        .kpi-card {
            border: 1px solid #6b6257;
            border-radius: 10px;
            background: #11141c;
            padding: 20px 22px;
            min-height: 116px;
        }
        .kpi-label {
            color: #d6c7ad;
            font-size: 14px;
            letter-spacing: .06em;
            text-transform: uppercase;
        }
        .kpi-value-blue {
            color: #57a8ff;
            font-size: 38px;
            font-weight: 800;
            margin-top: 8px;
        }
        .kpi-value-green {
            color: #4be7a8;
            font-size: 38px;
            font-weight: 800;
            margin-top: 8px;
        }
        .panel {
            border: 1px solid #6b6257;
            border-radius: 10px;
            background: #11141c;
            padding: 20px;
            margin-bottom: 20px;
        }
        .panel-title {
            font-weight: 800;
            font-size: 24px;
            color: #f7f4ef;
            margin-bottom: 10px;
        }
        .panel-kicker {
            color: #d6c7ad;
            letter-spacing: .06em;
            font-size: 13px;
            text-transform: uppercase;
        }
        .model-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-top: 12px;
        }
        .model-cell {
            border:1px solid #6b6257;
            border-radius:6px;
            padding:10px;
            background:#171c26;
        }
        .model-cell .label {
            color:#b8aa94;
            font-size:12px;
            text-transform:uppercase;
        }
        .model-cell .value {
            color:#5ba9ff;
            font-weight:800;
            margin-top:4px;
        }
        .overlay-row {
            border:1px solid #6b6257;
            border-radius:5px;
            padding:7px 10px;
            margin-top:8px;
            display:flex;
            justify-content:space-between;
        }
        .camera-strip {
            display:grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 10px;
            margin-top: 14px;
        }
        .camera-card {
            border:1px solid #6b6257;
            border-radius:8px;
            padding:12px;
            background:#171c26;
            min-height:82px;
        }
        .camera-card.active {border-color:#1faa8a;}
        .queue-svg {
            width:100%;
            height:190px;
            border:1px solid #6b6257;
            border-radius:10px;
            background:#11141c;
        }
        .footnote {
            color:#b8aa94;
            font-size:13px;
            margin-top:6px;
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


def presentation_strip(using_api: bool, speed: str) -> None:
    source = "API + generated demo telemetry" if using_api else "Standalone generated telemetry"
    st.markdown(
        f"""
        <div class="sim-strip">
            <div>
                <b>Simulation:</b> running @ {speed}
                <span class="sim-btn">1x</span>
                <span class="sim-btn sim-btn-active">{speed}</span>
                <span class="sim-btn">5x</span>
                <span class="source-note">source: {source}</span>
            </div>
            <div><span class="pill">READY FOR DEMO</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def top_header(store: str, health: dict, api_ok: bool) -> None:
    uptime = 76000 + int(time.time()) % 4000
    status = "Ok" if api_ok else "Demo"
    st.markdown(
        f"""
        <div class="topbar">
            <div>
                <div class="brand">Store Intelligence - live</div>
                <div class="subtitle">Real-time analytics for offline retail. Polls every 3s plus event stream.</div>
            </div>
            <div class="status-top">
                <span class="status-dot"></span>{status} <span style="color:#b8aa94;">- uptime {uptime}s</span>
                <span class="store-select">{store}</span>
                <div style="color:#9ca9bb;margin-top:10px;">{health["event_count"]} events loaded | {health["pos_loaded"]} POS transactions</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_row(metrics: dict) -> None:
    cards = [
        ("Unique visitors today", f"{metrics['unique_visitors']}", "blue"),
        ("Conversion rate", f"{metrics['conversion_rate'] * 100:.1f}%", "green"),
        ("Queue depth now", f"{metrics.get('queue_now', metrics['billing_queue_joins'])}", "green"),
        ("Abandonment", f"{metrics.get('abandonment_rate', 0) * 100:.1f}%", "green"),
    ]
    cols = st.columns(4)
    for col, (label, value, tone) in zip(cols, cards):
        with col:
            klass = "kpi-value-blue" if tone == "blue" else "kpi-value-green"
            st.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-label">{label}</div>
                    <div class="{klass}">{value}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def model_telemetry(speed: str) -> None:
    st.markdown(
        f"""
        <div class="panel-kicker">Model</div>
        <div style="display:grid;grid-template-columns:1fr 1.2fr;gap:6px;margin:8px 0 18px 0;">
            <div class="muted">Detector</div><div><b>YOLOv8n</b></div>
            <div class="muted">Tracker</div><div><b>ByteTrack-IoU</b></div>
            <div class="muted">Classes</div><div><b>Person [class_id: 0]</b></div>
            <div class="muted">Hardware</div><div><b>CPU inference</b></div>
        </div>
        <div class="panel-kicker">Telemetry</div>
        <div class="model-grid">
            <div class="model-cell"><div class="label">Mode</div><div class="value">SIM</div></div>
            <div class="model-cell"><div class="label">Speed</div><div class="value">{speed}</div></div>
            <div class="model-cell"><div class="label">Source</div><div class="value">Drawn</div></div>
            <div class="model-cell"><div class="label">Frames</div><div class="value">Live</div></div>
        </div>
        <div class="footnote">native: 30.0 fps</div>
        <div class="panel-kicker" style="margin-top:18px;">Active overlays (2)</div>
        <div class="overlay-row"><span><span class="status-dot"></span>Entry Threshold</span><span class="muted">LINE</span></div>
        <div class="overlay-row"><span><span style="display:inline-block;width:10px;height:10px;border-radius:999px;background:#2d7cd3;margin-right:7px;"></span>Entry Crossing Line</span><span class="muted">LINE</span></div>
        """,
        unsafe_allow_html=True,
    )


def camera_cards() -> None:
    cameras = [
        ("ENTRY", "Main Entrance", "CAM_1", True),
        ("FLOOR", "Main Floor", "CAM_2", False),
        ("FLOOR", "Secondary Floor", "CAM_3", False),
        ("BILLING", "Billing Counter", "CAM_4", False),
        ("BILLING", "Billing Queue", "CAM_5", False),
    ]
    html = ["<div class='camera-strip'>"]
    for role, name, cam, active in cameras:
        active_class = " active" if active else ""
        html.append(
            f"""
            <div class="camera-card{active_class}">
                <div class="muted" style="text-transform:uppercase;">{role}</div>
                <b>{name}</b><br>
                <span class="muted">{cam}</span>
            </div>
            """
        )
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)


def queue_panel(metrics: dict) -> None:
    values = metrics.get("queue_series", [metrics.get("queue_now", 0)])
    max_val = max(max(values), 6)
    points = []
    for idx, value in enumerate(values):
        x = 24 + idx * (420 / max(len(values) - 1, 1))
        y = 155 - (value / max_val) * 118
        points.append(f"{x:.1f},{y:.1f}")
    current = metrics.get("queue_now", values[-1] if values else 0)
    st.markdown(
        f"""
        <div class="panel">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div class="panel-kicker">Queue depth</div>
                <div class="kpi-value-green" style="font-size:30px;margin:0;">{current}</div>
            </div>
            <svg class="queue-svg" viewBox="0 0 470 190">
                <line x1="24" y1="155" x2="446" y2="155" stroke="#6b6257" stroke-width="1"/>
                <polyline points="{' '.join(points)}" fill="none" stroke="#36d9a7" stroke-width="3"/>
            </svg>
            <div class="footnote">rolling 60-sample window - critical at 6+</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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
    presentation_mode = st.sidebar.toggle("Presentation mode", value=True)
    speed = st.sidebar.selectbox("Simulation speed", ["1x", "2x", "5x"], index=1)

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
        api_health: dict | None = None
        if presentation_mode:
            using_standalone = True
            health, metrics, funnel, anomalies, events = standalone_demo()
            try:
                api_health = get_json(f"{api}/health")
            except requests.RequestException:
                api_health = None
        else:
            try:
                health = get_json(f"{api}/health")
                api_health = health
                metrics = get_json(f"{api}/stores/{store}/metrics")
                funnel = get_json(f"{api}/stores/{store}/funnel")
                anomalies = get_json(f"{api}/stores/{store}/anomalies")
                events = get_json(f"{api}/events?store_id={store}&limit=60")["events"]
            except requests.RequestException:
                using_standalone = True
                health, metrics, funnel, anomalies, events = standalone_demo()

        with placeholder.container():
            top_header(store, health, bool(api_health))
            presentation_strip(bool(api_health), speed)

            if "queue_series" not in metrics:
                current_queue = metrics.get("billing_queue_joins", 0)
                metrics["queue_series"] = [
                    max(0, current_queue + ((idx % 5) - 2 if idx > 18 else 0))
                    for idx in range(28)
                ]
                metrics["queue_now"] = current_queue

            kpi_row(metrics)

            left, right = st.columns([0.58, 0.42])
            with left:
                st.markdown("<div class='panel'>", unsafe_allow_html=True)
                st.markdown("<div class='panel-kicker'>YOLOv8 Live CV Stream</div><div class='panel-title'>Main Entrance <span class='muted'>(CAM_1)</span></div>", unsafe_allow_html=True)
                cv_cols = st.columns([0.72, 0.28])
                with cv_cols[0]:
                    camera_preview(metrics)
                with cv_cols[1]:
                    model_telemetry(speed)
                camera_cards()
                st.markdown("<div class='footnote'>Synthetic frames with bounding boxes, zone polygons and HUD. Drop licensed clips into data/clips to switch to real CCTV processing.</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

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
                queue_panel(metrics)

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
