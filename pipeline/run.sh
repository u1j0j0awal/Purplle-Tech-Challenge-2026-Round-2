#!/usr/bin/env bash
set -euo pipefail

VIDEO_DIR="${1:-../CCTV Footage}"
OUT="${2:-data/events.jsonl}"

python -m pipeline.detect --video-dir "$VIDEO_DIR" --out "$OUT" --stride "${STRIDE:-15}" --max-frames "${MAX_FRAMES:-0}"
