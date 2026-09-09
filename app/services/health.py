"""Health and system status checks."""

import logging
import sqlite3
from pathlib import Path

from app.core.config import settings
from app.database.db import get_connection
from app.engines.camera import camera_engine
from app.engines.vision import snapshot_dict, vision_engine

logger = logging.getLogger(__name__)


def _database_status() -> tuple[str, int]:
    try:
        with get_connection() as connection:
            table_count = connection.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table'"
            ).fetchone()[0]
        return "ok", table_count
    except (OSError, sqlite3.Error) as exc:
        logger.exception("Database health check failed: %s", exc)
        return "error", 0


def get_health() -> dict[str, object]:
    """Return component health without inventing operational telemetry."""

    database, table_count = _database_status()
    storage = "ok" if Path(settings.storage_path).is_dir() else "error"
    application = "ok"
    overall = "ok" if database == storage == application == "ok" else "degraded"
    return {
        "status": overall,
        "components": {
            "database": database,
            "storage": storage,
            "application": application,
        },
        "database_tables": table_count,
    }


def get_system_status() -> dict[str, object]:
    """Return persisted dashboard metrics plus the live camera engine state."""

    health = get_health()
    camera_snapshot = camera_engine.snapshot()
    vision_snapshot = vision_engine.snapshot()
    with get_connection() as connection:
        camera_total = connection.execute("SELECT COUNT(*) FROM cameras").fetchone()[0]
        camera_online = connection.execute(
            "SELECT COUNT(*) FROM cameras WHERE status = 'online'"
        ).fetchone()[0]
        known_presence = connection.execute(
            "SELECT COUNT(*) FROM attendance_sessions WHERE ended_at IS NULL"
        ).fetchone()[0]
        unrecognized_events = connection.execute(
            "SELECT COUNT(*) FROM security_events WHERE event_type = 'unrecognized'"
        ).fetchone()[0]
        open_incidents = connection.execute(
            "SELECT COUNT(*) FROM incidents WHERE status = 'open'"
        ).fetchone()[0]

    return {
        "system_status": health["status"],
        "security_index": None,
        "camera_status": {"online": camera_online, "total": camera_total},
        "camera_engine": {
            "status": camera_snapshot.status.value,
            "frames_received": camera_snapshot.frames_received,
            "last_frame_at": camera_snapshot.last_frame_at,
        },
        "vision_engine": snapshot_dict(vision_snapshot),
        "occupancy": {
            "current_people": vision_snapshot.person_count,
            "capacity": settings.occupancy_capacity,
            "occupancy_percent": round(vision_snapshot.person_count / settings.occupancy_capacity * 100, 1) if settings.occupancy_capacity else None,
        },
        "known_presence": known_presence,
        "unrecognized_events": unrecognized_events,
        "open_incidents": open_incidents,
        "system_health": health,
        "current_location": None,
        "ai_engines": {"person_detection": vision_snapshot.status, "face_recognition": "STANDBY", "behavior_analysis": "STANDBY"},
    }
