"""Optional local YOLO person detection with reusable model state."""

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from time import monotonic
from typing import Any

from app.core.config import settings
from app.engines.camera import CameraFrame
from app.engines.tracking import TrackingEngine


@dataclass(frozen=True)
class VisionSnapshot:
    status: str
    model: str
    person_count: int
    detections: list[dict[str, Any]]
    timestamp: datetime | None
    processing_latency_ms: float | None
    processed_frames: int
    processing_rate_fps: float | None
    error: str | None


class VisionEngine:
    """Run local person detection when optional runtime dependencies are available."""

    def __init__(
        self,
        model_name: str = "yolo11n.pt",
        confidence_threshold: float = 0.35,
        inference_interval: int = 1,
        frame_size: int = 640,
        detector_factory: Any | None = None,
    ) -> None:
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.inference_interval = max(1, inference_interval)
        self.frame_size = frame_size
        self._detector_factory = detector_factory
        self._model: Any | None = None
        self._initialized = False
        self._lock = Lock()
        self._frame_number = 0
        self._processed_frames = 0
        self._first_processed_at: float | None = None
        self._latest = VisionSnapshot("STANDBY", model_name, 0, [], None, None, 0, None, None)
        self.tracker = TrackingEngine()

    def _load_model(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        try:
            factory = self._detector_factory
            if factory is None:
                from ultralytics import YOLO

                factory = YOLO
            self._model = factory(self.model_name)
        except Exception as exc:
            self._latest = VisionSnapshot("UNAVAILABLE", self.model_name, 0, [], None, None, 0, None, str(exc))
            self._model = None

    @staticmethod
    def _decode_jpeg(payload: bytes) -> Any:
        if not payload or not payload.startswith(b"\xff\xd8") or not payload.endswith(b"\xff\xd9"):
            raise ValueError("Frame payload is not a valid JPEG")
        try:
            import cv2
            import numpy as np
        except ImportError as exc:
            raise RuntimeError("Vision dependencies unavailable: install opencv-python and numpy") from exc
        image = cv2.imdecode(np.frombuffer(payload, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None or image.size == 0:
            raise ValueError("Frame payload could not be decoded as JPEG")
        return image

    def process_frame(self, frame: CameraFrame) -> VisionSnapshot:
        with self._lock:
            self._frame_number += 1
            if self._frame_number % self.inference_interval != 0 and self._latest.status == "READY":
                return self._latest
            started = monotonic()
            try:
                image = self._decode_jpeg(frame.payload)
                self._load_model()
                if self._model is None:
                    return self._latest
                results = self._model.predict(source=image, imgsz=self.frame_size, conf=self.confidence_threshold, classes=[0], verbose=False)
                boxes: list[dict[str, int]] = []
                confidences: list[float] = []
                for result in results:
                    for box, confidence in zip(result.boxes.xyxy.tolist(), result.boxes.conf.tolist()):
                        boxes.append({"x1": max(0, int(box[0])), "y1": max(0, int(box[1])), "x2": int(box[2]), "y2": int(box[3])})
                        confidences.append(round(float(confidence), 4))
                track_ids = self.tracker.assign(boxes)
                detections = [
                    {"track_id": track_id, "label": "person", "bounding_box": box, "confidence": confidence}
                    for track_id, box, confidence in zip(track_ids, boxes, confidences)
                ]
                latency = round((monotonic() - started) * 1000, 2)
                self._processed_frames += 1
                self._first_processed_at = self._first_processed_at or monotonic()
                elapsed = monotonic() - self._first_processed_at
                rate = self._processed_frames / elapsed if elapsed > 0 else None
                self._latest = VisionSnapshot("READY", self.model_name, len(detections), detections, datetime.now(timezone.utc), latency, self._processed_frames, rate, None)
            except Exception as exc:
                self._latest = VisionSnapshot("UNAVAILABLE", self.model_name, 0, [], datetime.now(timezone.utc), round((monotonic() - started) * 1000, 2), self._processed_frames, None, str(exc))
            return self._latest

    def snapshot(self) -> VisionSnapshot:
        with self._lock:
            return self._latest


vision_engine = VisionEngine(
    model_name=settings.vision_model,
    confidence_threshold=settings.vision_confidence,
    inference_interval=settings.vision_interval,
    frame_size=settings.vision_frame_size,
)


def snapshot_dict(snapshot: VisionSnapshot) -> dict[str, Any]:
    return {
        "status": snapshot.status,
        "model": snapshot.model,
        "person_count": snapshot.person_count,
        "detections": snapshot.detections,
        "timestamp": snapshot.timestamp,
        "processing_latency_ms": snapshot.processing_latency_ms,
        "processed_frames": snapshot.processed_frames,
        "processing_rate_fps": snapshot.processing_rate_fps,
        "error": snapshot.error,
    }