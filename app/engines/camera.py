"""Browser-camera frame ingestion and health state."""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from threading import Lock
from typing import Callable


class CameraStatus(StrEnum):
    """Operational states shared by the browser camera UI and backend."""

    OFFLINE = "OFFLINE"
    REQUESTING = "REQUESTING"
    ONLINE = "ONLINE"
    ERROR = "ERROR"
    STOPPED = "STOPPED"


@dataclass(frozen=True)
class CameraFrame:
    """A locally received browser frame, ready for a future vision engine."""

    payload: bytes
    content_type: str
    received_at: datetime
    width: int | None = None
    height: int | None = None


@dataclass(frozen=True)
class CameraSnapshot:
    """Current engine state exposed to the API."""

    status: CameraStatus
    frames_received: int
    last_frame_at: datetime | None
    last_error: str | None


class CameraEngine:
    """Store the latest browser frame without performing detection yet."""

    def __init__(self, vision_hook: Callable[[CameraFrame], None] | None = None) -> None:
        self._lock = Lock()
        self._status = CameraStatus.OFFLINE
        self._frames_received = 0
        self._last_frame_at: datetime | None = None
        self._last_error: str | None = None
        self._latest_frame: CameraFrame | None = None
        self._vision_hook = vision_hook

    def set_status(self, status: CameraStatus, error: str | None = None) -> None:
        with self._lock:
            self._status = status
            self._last_error = error

    def receive_frame(
        self,
        payload: bytes,
        content_type: str = "image/jpeg",
        width: int | None = None,
        height: int | None = None,
    ) -> CameraFrame:
        if not payload:
            raise ValueError("Frame payload cannot be empty")
        if content_type != "image/jpeg":
            raise ValueError("Only image/jpeg frames are supported")
        if not payload.startswith(b"\xff\xd8") or not payload.endswith(b"\xff\xd9"):
            raise ValueError("Frame payload is not a valid JPEG")

        frame = CameraFrame(
            payload=payload,
            content_type=content_type,
            received_at=datetime.now(timezone.utc),
            width=width,
            height=height,
        )
        with self._lock:
            self._latest_frame = frame
            self._frames_received += 1
            self._last_frame_at = frame.received_at
            self._status = CameraStatus.ONLINE
            self._last_error = None
        if self._vision_hook is not None:
            self._vision_hook(frame)
        return frame

    def snapshot(self) -> CameraSnapshot:
        with self._lock:
            return CameraSnapshot(
                status=self._status,
                frames_received=self._frames_received,
                last_frame_at=self._last_frame_at,
                last_error=self._last_error,
            )


camera_engine = CameraEngine()
