"""Attendance Engine: Session-based real attendance tracking from confirmed presences."""

import logging
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from app.database.db import get_connection

logger = logging.getLogger(__name__)


class AttendanceEngine:
    """Manage attendance sessions from confirmed presences."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._active_sessions: dict[int, dict[str, Any]] = {}  # person_id -> session
        self._session_keys: dict[str, int] = {}  # deterministic key -> attendance_id for duplicate protection

    def _make_session_key(self, person_id: int, camera_id: int | None, location_id: int | None) -> str:
        """Create a deterministic session key to prevent duplicates."""
        return f"person_{person_id}_camera_{camera_id}_location_{location_id}"

    def create_or_update_session(
        self,
        person_id: int,
        person_name: str,
        track_id: int,
        location_id: int | None,
        camera_id: int | None,
        confidence: float,
        first_seen_at: datetime,
    ) -> int | None:
        """
        Create a new attendance session or update existing one.

        Returns:
            attendance_id if created or updated, None if error
        """
        with self._lock:
            session_key = self._make_session_key(person_id, camera_id, location_id)

            # Check if we already have an active session for this person+location+camera
            if session_key in self._session_keys:
                attendance_id = self._session_keys[session_key]
                # Update existing session
                try:
                    with get_connection() as conn:
                        conn.execute(
                            """
                            UPDATE attendance
                            SET last_seen_at = ?, confidence = ?, visit_count = visit_count + 1
                            WHERE id = ?
                            """,
                            (datetime.now(timezone.utc).isoformat(), confidence, attendance_id),
                        )
                        conn.commit()
                    return attendance_id
                except Exception as e:
                    logger.error(f"Failed to update attendance session: {e}")
                    return None

            # Create new session
            try:
                with get_connection() as conn:
                    cursor = conn.execute(
                        """
                        INSERT INTO attendance (
                            person_id, person_name, location_id, camera_id,
                            entry_time, first_seen_at, last_seen_at,
                            status, confidence, visit_count
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            person_id,
                            person_name,
                            location_id,
                            camera_id,
                            first_seen_at.isoformat(),
                            first_seen_at.isoformat(),
                            datetime.now(timezone.utc).isoformat(),
                            "PRESENT",
                            confidence,
                            1,
                        ),
                    )
                    conn.commit()
                    attendance_id = cursor.lastrowid
                    self._active_sessions[person_id] = {
                        "attendance_id": attendance_id,
                        "person_name": person_name,
                        "camera_id": camera_id,
                        "location_id": location_id,
                        "entry_time": first_seen_at,
                        "status": "PRESENT",
                    }
                    self._session_keys[session_key] = attendance_id
                    return attendance_id
            except Exception as e:
                logger.error(f"Failed to create attendance session: {e}")
                return None

    def finalize_session(
        self,
        person_id: int,
        camera_id: int | None,
        location_id: int | None,
        exit_time: datetime,
    ) -> bool:
        """Finalize an attendance session on exit."""
        with self._lock:
            session_key = self._make_session_key(person_id, camera_id, location_id)

            if session_key not in self._session_keys:
                return False

            attendance_id = self._session_keys[session_key]
            try:
                with get_connection() as conn:
                    # Get entry_time
                    result = conn.execute(
                        "SELECT entry_time FROM attendance WHERE id = ?",
                        (attendance_id,),
                    ).fetchone()

                    if not result:
                        return False

                    entry_time = datetime.fromisoformat(result[0])
                    duration_seconds = int((exit_time - entry_time).total_seconds())

                    conn.execute(
                        """
                        UPDATE attendance
                        SET exit_time = ?, duration_seconds = ?, status = ?
                        WHERE id = ?
                        """,
                        (
                            exit_time.isoformat(),
                            duration_seconds,
                            "COMPLETED",
                            attendance_id,
                        ),
                    )
                    conn.commit()

                    # Remove from active sessions
                    if person_id in self._active_sessions:
                        del self._active_sessions[person_id]
                    if session_key in self._session_keys:
                        del self._session_keys[session_key]

                    return True
            except Exception as e:
                logger.error(f"Failed to finalize attendance session: {e}")
                return False

    def get_today_attendance(self) -> list[dict[str, Any]]:
        """Get all attendance records for today."""
        try:
            with get_connection() as conn:
                conn.row_factory = None  # Reset to tuple mode temporarily
                cursor = conn.cursor()
                today = datetime.now(timezone.utc).date().isoformat()
                rows = cursor.execute(
                    """
                    SELECT
                        id, person_id, person_name, location_id, camera_id,
                        entry_time, exit_time, duration_seconds, status, confidence,
                        visit_count, created_at, updated_at
                    FROM attendance
                    WHERE DATE(entry_time) = ?
                    ORDER BY entry_time DESC
                    """,
                    (today,),
                ).fetchall()

                result = []
                for row in rows:
                    result.append(
                        {
                            "id": row[0],
                            "person_id": row[1],
                            "person_name": row[2],
                            "location_id": row[3],
                            "camera_id": row[4],
                            "entry_time": row[5],
                            "exit_time": row[6],
                            "duration_seconds": row[7],
                            "status": row[8],
                            "confidence": row[9],
                            "visit_count": row[10],
                            "created_at": row[11],
                            "updated_at": row[12],
                        }
                    )
                return result
        except Exception as e:
            logger.error(f"Failed to get today's attendance: {e}")
            return []

    def get_attendance(
        self,
        person_id: int | None = None,
        location_id: int | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get attendance records with optional filters."""
        try:
            with get_connection() as conn:
                conn.row_factory = None
                query = "SELECT id, person_id, person_name, location_id, camera_id, entry_time, exit_time, duration_seconds, status, confidence, visit_count, created_at, updated_at FROM attendance"
                params = []
                conditions = []

                if person_id is not None:
                    conditions.append("person_id = ?")
                    params.append(person_id)
                if location_id is not None:
                    conditions.append("location_id = ?")
                    params.append(location_id)
                if status is not None:
                    conditions.append("status = ?")
                    params.append(status)

                if conditions:
                    query += " WHERE " + " AND ".join(conditions)

                query += " ORDER BY entry_time DESC LIMIT ?"
                params.append(limit)

                rows = conn.execute(query, params).fetchall()
                result = []
                for row in rows:
                    result.append(
                        {
                            "id": row[0],
                            "person_id": row[1],
                            "person_name": row[2],
                            "location_id": row[3],
                            "camera_id": row[4],
                            "entry_time": row[5],
                            "exit_time": row[6],
                            "duration_seconds": row[7],
                            "status": row[8],
                            "confidence": row[9],
                            "visit_count": row[10],
                            "created_at": row[11],
                            "updated_at": row[12],
                        }
                    )
                return result
        except Exception as e:
            logger.error(f"Failed to get attendance: {e}")
            return []

    def get_attendance_by_id(self, attendance_id: int) -> dict[str, Any] | None:
        """Get a specific attendance record."""
        try:
            with get_connection() as conn:
                conn.row_factory = None
                row = conn.execute(
                    """
                    SELECT id, person_id, person_name, location_id, camera_id,
                           entry_time, exit_time, duration_seconds, status, confidence,
                           visit_count, created_at, updated_at
                    FROM attendance WHERE id = ?
                    """,
                    (attendance_id,),
                ).fetchone()

                if not row:
                    return None

                return {
                    "id": row[0],
                    "person_id": row[1],
                    "person_name": row[2],
                    "location_id": row[3],
                    "camera_id": row[4],
                    "entry_time": row[5],
                    "exit_time": row[6],
                    "duration_seconds": row[7],
                    "status": row[8],
                    "confidence": row[9],
                    "visit_count": row[10],
                    "created_at": row[11],
                    "updated_at": row[12],
                }
        except Exception as e:
            logger.error(f"Failed to get attendance {attendance_id}: {e}")
            return None

    def get_stats(self) -> dict[str, Any]:
        """Get attendance statistics."""
        try:
            with get_connection() as conn:
                today = datetime.now(timezone.utc).date().isoformat()

                today_entries = conn.execute(
                    "SELECT COUNT(*) FROM attendance WHERE DATE(entry_time) = ?",
                    (today,),
                ).fetchone()[0]

                today_completed = conn.execute(
                    "SELECT COUNT(*) FROM attendance WHERE DATE(entry_time) = ? AND status = ?",
                    (today, "COMPLETED"),
                ).fetchone()[0]

                today_present = conn.execute(
                    "SELECT COUNT(*) FROM attendance WHERE DATE(entry_time) = ? AND status = ?",
                    (today, "PRESENT"),
                ).fetchone()[0]

                total_visits = conn.execute(
                    "SELECT COUNT(*) FROM attendance",
                ).fetchone()[0]

                unique_people_today = conn.execute(
                    "SELECT COUNT(DISTINCT person_id) FROM attendance WHERE DATE(entry_time) = ?",
                    (today,),
                ).fetchone()[0]

                return {
                    "today_entries": today_entries,
                    "today_completed": today_completed,
                    "today_present": today_present,
                    "total_visits": total_visits,
                    "unique_people_today": unique_people_today,
                }
        except Exception as e:
            logger.error(f"Failed to get attendance stats: {e}")
            return {
                "today_entries": 0,
                "today_completed": 0,
                "today_present": 0,
                "total_visits": 0,
                "unique_people_today": 0,
            }


# Global attendance engine instance
attendance_engine = AttendanceEngine()
