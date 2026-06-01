from __future__ import annotations

import json
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
        .block-container {padding-top: 1.4rem; max-width: 1440px;}
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
        </style>
        """,
        unsafe_allow_html=True,
    )


def get_json(url: str) -> dict:
    response = requests.get(url, timeout=5)
    response.raise_for_status()
    return response.json()


def standalone_demo() -> tuple[dict, dict, dict, dict, list[dict]]:
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
    metrics = {
        "unique_visitors": 2,
        "purchases": 2,
        "conversion_rate": 1.0,
        "revenue_inr": 9491.21,
        "billing_queue_joins": 2,
        "avg_confidence": 0.808,
        "reentries": 1,
        "zone_dwell_ms": {"MAKEUP": 30000, "BILLING": 0, "SKINCARE": 0},
        "zone_unique_visitors": {"MAKEUP": 1, "BILLING": 2, "SKINCARE": 1},
    }
    funnel = {
        "stages": [
            {"stage": "entry", "visitors": 2},
            {"stage": "browse", "visitors": 2},
            {"stage": "billing_intent", "visitors": 2},
            {"stage": "purchase", "visitors": 2},
        ]
    }
    health = {"event_count": 10, "pos_loaded": 24}
    anomalies = {"anomalies": [], "count": 0}
    return health, metrics, funnel, anomalies, events


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

            st.write("")
            kpi = st.columns(5)
            kpi[0].metric("Visitors", metrics["unique_visitors"])
            kpi[1].metric("Purchases", metrics["purchases"])
            kpi[2].metric("Conversion", f"{metrics['conversion_rate'] * 100:.1f}%")
            kpi[3].metric("Revenue", f"INR {metrics['revenue_inr']:,.0f}")
            kpi[4].metric("Queue joins", metrics["billing_queue_joins"])

            left, right = st.columns([0.58, 0.42])
            with left:
                st.subheader("Customer Funnel")
                st.markdown("<div class='hero'>", unsafe_allow_html=True)
                funnel_progress(funnel["stages"])
                st.markdown("</div>", unsafe_allow_html=True)

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

            st.caption(f"Last refreshed at {pd.Timestamp.now().strftime('%H:%M:%S')}")

        if not auto_refresh:
            break
        time.sleep(refresh)


if __name__ == "__main__":
    main()
