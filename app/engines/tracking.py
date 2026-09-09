"""Lightweight temporary tracking for nearby person detections."""

from dataclasses import dataclass
from math import hypot
from threading import Lock


@dataclass
class _Track:
    track_id: int
    center_x: float
    center_y: float
    missed_frames: int = 0


class TrackingEngine:
    """Match detections by nearby bounding-box centers without face identity."""

    def __init__(self, max_distance: float = 80.0, max_missed_frames: int = 4) -> None:
        self._lock = Lock()
        self._max_distance = max_distance
        self._max_missed_frames = max_missed_frames
        self._next_id = 1
        self._tracks: list[_Track] = []

    def assign(self, boxes: list[dict[str, int]]) -> list[int]:
        with self._lock:
            assigned: list[int] = []
            used_tracks: set[int] = set()
            for box in boxes:
                center_x = (box["x1"] + box["x2"]) / 2
                center_y = (box["y1"] + box["y2"]) / 2
                candidates = [track for track in self._tracks if track.track_id not in used_tracks]
                match = min(candidates, key=lambda track: hypot(track.center_x - center_x, track.center_y - center_y), default=None)
                if match is not None and hypot(match.center_x - center_x, match.center_y - center_y) <= self._max_distance:
                    match.center_x = center_x
                    match.center_y = center_y
                    match.missed_frames = 0
                    used_tracks.add(match.track_id)
                    assigned.append(match.track_id)
                else:
                    match = _Track(self._next_id, center_x, center_y)
                    self._next_id += 1
                    self._tracks.append(match)
                    used_tracks.add(match.track_id)
                    assigned.append(match.track_id)
            for track in self._tracks:
                if track.track_id not in used_tracks:
                    track.missed_frames += 1
            self._tracks = [track for track in self._tracks if track.missed_frames <= self._max_missed_frames]
            return assigned