"""Presence Engine: Track currently present people, detect first appearance, maintain presence state."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any


@dataclass
class PresenceState:
    """Current presence status of a tracked person."""

    track_id: int
    identity_id: int | None = None  # Identity confirmed by Phase 4
    person_id: int | None = None  # Registered person ID
    person_name: str | None = None
    first_seen_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    confidence: float = 0.0
    status: str = "UNKNOWN"  # PRESENT, ABSENT, EXITED, UNKNOWN
    location: str | None = None
    camera_id: int | None = None


class PresenceEngine:
    """Track currently present people from vision detections and identity confirmations."""

    def __init__(
        self,
        entry_confirmation_seconds: int = 3,
        exit_grace_seconds: int = 5,
    ) -> None:
        self._lock = Lock()
        self._entry_confirmation_seconds = entry_confirmation_seconds
        self._exit_grace_seconds = exit_grace_seconds
        self._presence_states: dict[int, PresenceState] = {}  # track_id -> PresenceState
        self._recent_detections: dict[int, datetime] = {}  # track_id -> last detection time

    def update_detection(
        self,
        track_id: int,
        confidence: float = 0.0,
        identity_id: int | None = None,
        person_id: int | None = None,
        person_name: str | None = None,
        location: str | None = None,
        camera_id: int | None = None,
    ) -> tuple[bool, str]:
        """
        Update presence state with a new detection.

        Returns:
            (is_new_entry, status) - True if this is a new entry, status string
        """
        with self._lock:
            now = datetime.now(timezone.utc)
            is_new_entry = False
            entry_status = "UNKNOWN"

            if track_id not in self._presence_states:
                # First detection of this track
                state = PresenceState(
                    track_id=track_id,
                    identity_id=identity_id,
                    person_id=person_id,
                    person_name=person_name,
                    first_seen_at=now,
                    last_seen_at=now,
                    confidence=confidence,
                    status="UNKNOWN",
                    location=location,
                    camera_id=camera_id,
                )
                self._presence_states[track_id] = state
                self._recent_detections[track_id] = now
                entry_status = "UNKNOWN"
            else:
                # Update existing track
                state = self._presence_states[track_id]
                state.last_seen_at = now
                state.confidence = max(state.confidence, confidence)

                if identity_id is not None:
                    state.identity_id = identity_id
                if person_id is not None:
                    state.person_id = person_id
                if person_name is not None:
                    state.person_name = person_name
                if location is not None:
                    state.location = location
                if camera_id is not None:
                    state.camera_id = camera_id

                # Check entry confirmation threshold
                time_since_first_seen = (now - state.first_seen_at).total_seconds()
                if state.status == "UNKNOWN" and time_since_first_seen >= self._entry_confirmation_seconds:
                    # Confirmed presence
                    state.status = "PRESENT"
                    is_new_entry = True
                    entry_status = "CONFIRMED"
                elif state.status == "UNKNOWN":
                    entry_status = "PENDING"
                else:
                    entry_status = state.status

                self._recent_detections[track_id] = now

            return is_new_entry, entry_status

    def mark_missed(self, track_id: int) -> tuple[bool, str]:
        """
        Mark a track as not detected in current frame.

        Returns:
            (is_exit, status) - True if person is now exited, status string
        """
        with self._lock:
            now = datetime.now(timezone.utc)
            is_exit = False
            exit_status = "NO_ACTION"

            if track_id in self._recent_detections:
                time_since_last_detection = (now - self._recent_detections[track_id]).total_seconds()

                if time_since_last_detection >= self._exit_grace_seconds:
                    if track_id in self._presence_states:
                        state = self._presence_states[track_id]
                        if state.status == "PRESENT":
                            state.status = "EXITED"
                            is_exit = True
                            exit_status = "CONFIRMED"
                        elif state.status == "UNKNOWN":
                            state.status = "ABSENT"
                            exit_status = "ABSENT"

            return is_exit, exit_status

    def get_current_presence(self) -> dict[int, PresenceState]:
        """Return all currently tracked people still in PRESENT or UNKNOWN state."""
        with self._lock:
            return {
                track_id: state
                for track_id, state in self._presence_states.items()
                if state.status in ("PRESENT", "UNKNOWN")
            }

    def get_presence_for_person(self, person_id: int) -> PresenceState | None:
        """Get current presence state for a registered person."""
        with self._lock:
            for state in self._presence_states.values():
                if state.person_id == person_id and state.status in ("PRESENT", "UNKNOWN"):
                    return state
            return None

    def get_presence_for_track(self, track_id: int) -> PresenceState | None:
        """Get presence state for a specific track."""
        with self._lock:
            return self._presence_states.get(track_id)

    def clear_exited(self) -> None:
        """Remove EXITED and ABSENT tracks from active tracking (call periodically)."""
        with self._lock:
            self._presence_states = {
                track_id: state
                for track_id, state in self._presence_states.items()
                if state.status not in ("EXITED", "ABSENT")
            }
            self._recent_detections = {
                track_id: time
                for track_id, time in self._recent_detections.items()
                if track_id in self._presence_states
            }

    def snapshot(self) -> dict[str, Any]:
        """Return current presence snapshot."""
        with self._lock:
            states = self.get_current_presence()
            return {
                "active_tracks": len(states),
                "total_tracked": len(self._presence_states),
                "present_people": len([s for s in states.values() if s.status == "PRESENT"]),
                "unknown_people": len([s for s in states.values() if s.status == "UNKNOWN"]),
                "registered_present": len([s for s in states.values() if s.person_id and s.status == "PRESENT"]),
            }


# Global presence engine instance
presence_engine = PresenceEngine(
    entry_confirmation_seconds=3,
    exit_grace_seconds=5,
)
