# Choices

## 1. Detection Model

Options considered: YOLOv8/YOLOv9, RT-DETR, MediaPipe and pure motion detection. AI suggested YOLOv8 as the default because it is small, well-documented, fast on CPU for sampled frames, and already trained on the `person` class. I chose YOLOv8 nano through Ultralytics for the submitted pipeline.

The reason is pragmatic. The challenge is not asking for a novel detector; it is asking for a working store intelligence system. YOLOv8 gives acceptable person detections on anonymized CCTV, supports confidence scores, and works without labelled training data. RT-DETR may be stronger in some crowded cases, but it is heavier. Motion detection is tempting for entry counting, but it collapses groups into blobs and fails around lighting changes, reflections and stationary browsing.

The main weakness is staff/customer separation. A detector trained only on people does not know Purplle uniforms. I document the limitation and use camera-role plus heuristic staff flags. If this were production, I would collect 200-500 annotated staff/customer examples from each store format and add a small uniform classifier or ReID embedding model.

## 2. Event Schema

Options considered: only aggregate counters, one row per detection frame, or semantic visitor events. AI recommended semantic events because they support all required endpoints without forcing the API to understand video frames. I chose semantic events matching the problem statement: `ENTRY`, `EXIT`, `ZONE_ENTER`, `ZONE_EXIT`, `ZONE_DWELL`, `BILLING_QUEUE_JOIN`, `BILLING_QUEUE_ABANDON` and `REENTRY`.

The schema keeps raw CV uncertainty available through `confidence` and `metadata.bbox`, but it does not leak implementation-only frame data into business APIs. `visitor_id` is session-scoped so the analytics layer can deduplicate visitors and compute funnel stages. `event_id` enables idempotent ingestion, which is essential because real pipelines retry batches.

The deliberate compromise is that the API trusts event semantics. It validates schema and computes metrics, but it does not re-run CV. That separation keeps the system maintainable: a better tracker can improve events later while the API contract remains stable.

## 3. API and Storage

Options considered: in-memory only, SQLite, PostgreSQL, Kafka plus a database, and append-only JSONL. AI suggested SQLite as a safe default. I chose append-only JSONL for the take-home submission because the reviewer can inspect generated events immediately, Docker runs with one service, and the code stays simple enough to audit in minutes.

The API is still production-aware: ingestion is idempotent by `event_id`, malformed events produce partial success instead of 500s, `/health` exposes state, and Docker Compose runs the service without manual setup. For 40 live stores, the first thing I would replace is storage and ingestion fan-in: events should land in Kafka or Pub/Sub, then be materialized into PostgreSQL/ClickHouse for queryable analytics.

This choice optimizes for the scoring environment. Reviewers have a short evaluation window, so inspectability and deterministic startup matter more than theoretical scale. The code names this trade-off clearly rather than pretending JSONL is the final architecture for high-volume retail telemetry.
