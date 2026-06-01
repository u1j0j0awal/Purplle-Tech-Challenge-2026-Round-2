from __future__ import annotations

from dataclasses import dataclass, field

from pipeline.geometry import centroid, iou


@dataclass
class Track:
    track_id: int
    box: tuple[float, float, float, float]
    confidence: float
    first_frame: int
    last_frame: int
    missed: int = 0
    zones: set[str] = field(default_factory=set)
    entry_state: str | None = None
    visitor_id: str | None = None
    session_seq: int = 0
    last_dwell_emit_s: dict[str, float] = field(default_factory=dict)

    @property
    def center(self) -> tuple[float, float]:
        return centroid(self.box)


class CentroidTracker:
    def __init__(self, max_missed: int = 8, min_iou: float = 0.05):
        self.max_missed = max_missed
        self.min_iou = min_iou
        self.next_id = 1
        self.tracks: dict[int, Track] = {}

    def update(self, detections: list[tuple[tuple[float, float, float, float], float]], frame_no: int) -> list[Track]:
        unmatched = set(range(len(detections)))
        for track in list(self.tracks.values()):
            best_idx = None
            best_score = 0.0
            for idx in unmatched:
                score = iou(track.box, detections[idx][0])
                if score > best_score:
                    best_score = score
                    best_idx = idx
            if best_idx is not None and best_score >= self.min_iou:
                box, conf = detections[best_idx]
                track.box = box
                track.confidence = conf
                track.last_frame = frame_no
                track.missed = 0
                unmatched.remove(best_idx)
            else:
                track.missed += 1

        for idx in unmatched:
            box, conf = detections[idx]
            self.tracks[self.next_id] = Track(self.next_id, box, conf, frame_no, frame_no)
            self.next_id += 1

        expired = [tid for tid, t in self.tracks.items() if t.missed > self.max_missed]
        for tid in expired:
            del self.tracks[tid]
        return list(self.tracks.values())
