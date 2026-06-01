from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import cv2

from pipeline.emit import clip_timestamp, make_event, write_jsonl
from pipeline.geometry import point_in_polygon
from pipeline.tracker import CentroidTracker, Track

STORE_ID = "STORE_BLR_002"


def load_model(model_name: str):
    from ultralytics import YOLO

    return YOLO(model_name)


def camera_id_from_path(path: Path) -> str:
    match = re.search(r"CAM\s*(\d+)", path.stem, re.I)
    return f"CAM_{match.group(1)}" if match else path.stem.upper().replace(" ", "_")


def detect_people(model, frame, conf: float) -> list[tuple[tuple[float, float, float, float], float]]:
    result = model.predict(frame, classes=[0], conf=conf, verbose=False)[0]
    detections = []
    for box in result.boxes:
        x1, y1, x2, y2 = [float(x) for x in box.xyxy[0].tolist()]
        detections.append(((x1, y1, x2, y2), float(box.conf[0])))
    return detections


def state_for_entry_line(track: Track, entry_line_y: float, inside_lower: bool) -> str:
    _, y = track.center
    if inside_lower:
        return "inside" if y >= entry_line_y else "outside"
    return "inside" if y <= entry_line_y else "outside"


def likely_staff(camera_id: str, track: Track) -> bool:
    if camera_id == "CAM_4":
        return True
    x1, y1, x2, y2 = track.box
    height = max(1, y2 - y1)
    width = max(1, x2 - x1)
    return camera_id in {"CAM_1", "CAM_2", "CAM_5"} and height / width > 2.8 and track.confidence < 0.55


def process_video(video_path: Path, layout: dict, model, args) -> list[dict]:
    camera_id = camera_id_from_path(video_path)
    camera_cfg = layout["cameras"].get(camera_id, {})
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    tracker = CentroidTracker(max_missed=6)
    frame_no = 0
    events: list[dict] = []
    seen_exited: dict[int, str] = {}
    start_ts = args.start_time

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if frame_no % args.stride != 0:
            frame_no += 1
            continue

        detections = detect_people(model, frame, args.conf)
        tracks = tracker.update(detections, frame_no)
        ts = clip_timestamp(start_ts, frame_no / fps)

        for track in tracks:
            visitor_id = track.visitor_id or f"VIS_{camera_id}_{track.track_id:04d}"
            track.visitor_id = visitor_id
            is_staff = likely_staff(camera_id, track)
            metadata = {"track_id": track.track_id, "session_seq": track.session_seq, "bbox": [round(v, 1) for v in track.box]}

            if camera_cfg.get("role") == "entry_exit":
                current_state = state_for_entry_line(
                    track,
                    float(camera_cfg.get("entry_line_y", 520)),
                    bool(camera_cfg.get("entry_inside_is_lower_y", True)),
                )
                previous = track.entry_state
                track.entry_state = current_state
                if previous == "outside" and current_state == "inside":
                    event_type = "REENTRY" if track.track_id in seen_exited else "ENTRY"
                    track.session_seq += 1
                    events.append(
                        make_event(
                            store_id=STORE_ID,
                            camera_id=camera_id,
                            visitor_id=visitor_id,
                            event_type=event_type,
                            timestamp=ts,
                            zone_id=None,
                            is_staff=is_staff,
                            confidence=track.confidence,
                            metadata={**metadata, "direction": "inbound"},
                        )
                    )
                elif previous == "inside" and current_state == "outside":
                    seen_exited[track.track_id] = visitor_id
                    track.session_seq += 1
                    events.append(
                        make_event(
                            store_id=STORE_ID,
                            camera_id=camera_id,
                            visitor_id=visitor_id,
                            event_type="EXIT",
                            timestamp=ts,
                            zone_id=None,
                            is_staff=is_staff,
                            confidence=track.confidence,
                            metadata={**metadata, "direction": "outbound"},
                        )
                    )

            for zone in camera_cfg.get("zones", []):
                zone_id = zone["zone_id"]
                inside = point_in_polygon(track.center, zone["polygon"])
                was_inside = zone_id in track.zones
                if inside and not was_inside:
                    track.zones.add(zone_id)
                    track.session_seq += 1
                    event_type = "BILLING_QUEUE_JOIN" if zone_id == "BILLING" else "ZONE_ENTER"
                    queue_depth = sum(1 for t in tracks if zone_id in t.zones and not likely_staff(camera_id, t))
                    events.append(
                        make_event(
                            store_id=STORE_ID,
                            camera_id=camera_id,
                            visitor_id=visitor_id,
                            event_type=event_type,
                            timestamp=ts,
                            zone_id=zone_id,
                            is_staff=is_staff,
                            confidence=track.confidence,
                            metadata={**metadata, "sku_zone": zone.get("sku_zone"), "queue_depth": queue_depth if zone_id == "BILLING" else None},
                        )
                    )
                elif not inside and was_inside:
                    track.zones.remove(zone_id)
                    track.session_seq += 1
                    events.append(
                        make_event(
                            store_id=STORE_ID,
                            camera_id=camera_id,
                            visitor_id=visitor_id,
                            event_type="ZONE_EXIT",
                            timestamp=ts,
                            zone_id=zone_id,
                            is_staff=is_staff,
                            confidence=track.confidence,
                            metadata={**metadata, "sku_zone": zone.get("sku_zone")},
                        )
                    )
                elif inside:
                    elapsed_s = frame_no / fps
                    last_emit = track.last_dwell_emit_s.get(zone_id, elapsed_s)
                    if elapsed_s - last_emit >= args.dwell_seconds:
                        track.last_dwell_emit_s[zone_id] = elapsed_s
                        track.session_seq += 1
                        events.append(
                            make_event(
                                store_id=STORE_ID,
                                camera_id=camera_id,
                                visitor_id=visitor_id,
                                event_type="ZONE_DWELL",
                                timestamp=ts,
                                zone_id=zone_id,
                                dwell_ms=int(args.dwell_seconds * 1000),
                                is_staff=is_staff,
                                confidence=track.confidence,
                                metadata={**metadata, "sku_zone": zone.get("sku_zone")},
                            )
                        )
        frame_no += 1
        if args.max_frames and frame_no >= args.max_frames:
            break
    cap.release()
    return events


def demo_events() -> list[dict]:
    base = datetime(2026, 4, 10, 12, 15, tzinfo=timezone.utc)
    rows = [
        ("VIS_DEMO_001", "ENTRY", "CAM_3", None, 0, 0.91, 0),
        ("VIS_DEMO_001", "ZONE_ENTER", "CAM_2", "MAKEUP", 0, 0.88, 90),
        ("VIS_DEMO_001", "ZONE_DWELL", "CAM_2", "MAKEUP", 30000, 0.86, 125),
        ("VIS_DEMO_001", "BILLING_QUEUE_JOIN", "CAM_5", "BILLING", 0, 0.82, 600),
        ("VIS_DEMO_001", "EXIT", "CAM_3", None, 0, 0.89, 960),
        ("VIS_DEMO_002", "ENTRY", "CAM_3", None, 0, 0.78, 1200),
        ("VIS_DEMO_002", "ZONE_ENTER", "CAM_1", "SKINCARE", 0, 0.73, 1260),
        ("VIS_DEMO_002", "BILLING_QUEUE_JOIN", "CAM_5", "BILLING", 0, 0.76, 1680),
        ("VIS_DEMO_002", "EXIT", "CAM_3", None, 0, 0.74, 1800),
        ("VIS_DEMO_002", "REENTRY", "CAM_3", None, 0, 0.71, 1860),
    ]
    events = []
    for i, (visitor, kind, camera, zone, dwell, conf, offset) in enumerate(rows):
        event = make_event(
            store_id=STORE_ID,
            camera_id=camera,
            visitor_id=visitor,
            event_type=kind,
            timestamp=base.replace() + __import__("datetime").timedelta(seconds=offset),
            zone_id=zone,
            dwell_ms=dwell,
            confidence=conf,
            metadata={"session_seq": i + 1, "queue_depth": 2 if kind == "BILLING_QUEUE_JOIN" else None},
        )
        event["event_id"] = f"demo-{i + 1:03d}"
        events.append(event)
    return events


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect people and emit Store Intelligence events.")
    parser.add_argument("--video-dir", type=Path, default=Path("../CCTV Footage"))
    parser.add_argument("--layout", type=Path, default=Path("data/store_layout.json"))
    parser.add_argument("--out", type=Path, default=Path("data/events.jsonl"))
    parser.add_argument("--model", default="yolov8n.pt")
    parser.add_argument("--conf", type=float, default=0.35)
    parser.add_argument("--stride", type=int, default=15)
    parser.add_argument("--dwell-seconds", type=int, default=30)
    parser.add_argument("--max-frames", type=int, default=0)
    parser.add_argument("--demo", action="store_true", help="Emit deterministic demo events if clips are unavailable.")
    parser.add_argument("--start-time", type=lambda s: datetime.fromisoformat(s).astimezone(timezone.utc), default=datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc))
    args = parser.parse_args()

    if args.demo:
        events = demo_events()
    else:
        layout = json.loads(args.layout.read_text(encoding="utf-8"))
        model = load_model(args.model)
        events = []
        for video in sorted(args.video_dir.glob("CAM *.mp4")):
            events.extend(process_video(video, layout, model, args))
    write_jsonl(events, args.out)
    print(f"wrote {len(events)} events to {args.out}")


if __name__ == "__main__":
    main()
