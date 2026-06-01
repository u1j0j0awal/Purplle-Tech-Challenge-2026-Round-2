# Design

## Goal

This project optimizes for the challenge's north-star metric: offline store conversion rate. The system starts with raw CCTV clips and ends with APIs that answer business questions: how many customers entered, how many bought, where they spent time, where they dropped off, and whether operations need attention.

The implementation is intentionally production-shaped rather than model-showcase-shaped. Detection accuracy matters, but the acceptance gate and scoring framework reward a system that runs, emits valid events, handles edge cases and exposes coherent analytics. For that reason the design separates computer vision from business logic. The pipeline can improve over time without rewriting the API.

## Architecture

The system has four layers.

1. Detection and tracking: `pipeline/detect.py` reads CCTV clips, runs YOLO person detection, assigns short-lived track IDs with `pipeline/tracker.py`, and maps track centroids into calibrated camera polygons from `data/store_layout.json`.
2. Event emission: `pipeline/emit.py` produces JSONL events matching the required schema: globally unique event ID, store, camera, visitor, event type, timestamp, zone, dwell, staff flag, confidence and metadata.
3. Intelligence API: `app/main.py` exposes `POST /events/ingest`, `GET /stores/{id}/metrics`, `/funnel`, `/heatmap`, `/anomalies`, `/health`, plus `/metrics` and `/Metrics` aliases for acceptance-gate compatibility.
4. Live dashboard: `dashboard/app.py` polls the API and renders conversion, revenue, queue pressure, dwell and anomalies in real time.

## Data Flow

The CV pipeline is batch-friendly and stream-friendly. In batch mode it writes `data/events.jsonl`. In streaming mode the same event objects can be posted to `/events/ingest` in batches of up to 500. The API validates each event independently, deduplicates by `event_id`, and persists accepted events to JSONL so a container restart does not wipe state.

POS transactions are loaded from `data/pos_transactions.csv`. The helper script converts the provided item-level Purplle CSV into transaction rows. If the richer item-level file is present directly, `app/pos.py` can also collapse invoices on the fly. Session-to-purchase correlation uses a practical time window: purchases within ten minutes before a session and forty-five minutes after last sighting can attach to that visitor. This is not perfect identity matching, but it is explainable and robust under the given anonymized footage constraints.

## Edge Cases

Group entry is handled by person-level detections rather than blob-level motion. If YOLO sees three people crossing the entry threshold together, three tracks can emit three entries.

Re-entry is represented explicitly. CAM 3 is the source of truth for entry/exit. When a track crosses out and later crosses in again, the pipeline emits `REENTRY` instead of a fresh `ENTRY`.

Staff movement is excluded from customer metrics. CAM 4 is stock-room/back-room footage and is treated as staff-only. Other cameras use a conservative staff heuristic based on camera role and detection shape/confidence. This is documented as a known limitation: a uniform classifier or ReID embedding would be better if more labelled examples were available.

Occlusion and uncertainty are handled by confidence propagation. Low-confidence detections are not silently promoted; confidence stays attached to events and metrics expose average confidence.

Zero-traffic periods return valid JSON with zero visitors, zero purchases and zero conversion. Tests cover this because null or division-by-zero behavior is a common analytics failure.

## Observability and Operations

The API has `/health` with event count, storage path and POS load count. Docker Compose includes a health check. Ingestion returns accepted, duplicate and rejected counts with structured errors. Event storage is deliberately simple JSONL for the take-home setting; it is easy to inspect and easy to replace with PostgreSQL or Kafka-backed consumers in production.

## AI-Assisted Decisions

AI helped pressure-test the architecture against the published scoring rubric. The useful suggestion was to prioritize idempotent APIs and non-trivial docs before chasing perfect CV accuracy, because the acceptance gate rejects systems that cannot run. I agreed with that ordering.

AI suggested using a heavy tracker such as DeepSORT. I overrode that for the first submission because the footage is short, the challenge allows reasonable trade-offs, and a transparent centroid/IoU tracker is easier to defend in follow-up questions. The code boundary still permits replacing `CentroidTracker` later.

AI also suggested a VLM for zone classification. I chose calibrated polygons instead because store zones are spatial and stable. A VLM could label shelves during calibration, but using it frame-by-frame would add latency, cost and nondeterminism without improving the core conversion calculation.
