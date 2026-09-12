"""API and dashboard routes - Phases 1-5."""

import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.database.db import get_connection
from app.engines.attendance import attendance_engine
from app.engines.camera import camera_engine
from app.engines.presence import presence_engine
from app.engines.vision import snapshot_dict, vision_engine
from app.services.health import get_health, get_system_status

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).resolve().parents[2] / "frontend" / "templates")


# ============ Dashboard & Core Routes ============


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request) -> HTMLResponse:
    """Main dashboard."""
    try:
        status = get_system_status()
        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={"status": status},
        )
    except Exception:
        logger.exception("Unable to render dashboard")
        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={"status": {"system_status": "degraded", "system_health": {"status": "error"}}},
            status_code=503,
        )


@router.get("/health")
def health() -> dict[str, object]:
    """Health check."""
    return get_health()


@router.get("/api/system/status")
def system_status() -> dict[str, object]:
    """System status including all engines."""
    return get_system_status()


# ============ Camera & Vision Routes (Phase 2-3) ============


@router.get("/camera", response_class=HTMLResponse)
def camera_page(request: Request) -> HTMLResponse:
    """Live camera page."""
    return templates.TemplateResponse(request=request, name="camera.html", context={})


@router.get("/api/camera/test")
def camera_test() -> dict[str, object]:
    """Camera engine test endpoint."""
    snapshot = camera_engine.snapshot()
    return {
        "service": "camera-engine",
        "status": snapshot.status,
        "frames_received": snapshot.frames_received,
        "last_frame_at": snapshot.last_frame_at,
        "ready_for_browser_frames": True,
        "vision": snapshot_dict(vision_engine.snapshot()),
    }


@router.get("/api/vision/status")
def vision_status() -> dict[str, object]:
    """Vision engine status."""
    return snapshot_dict(vision_engine.snapshot())


@router.post("/api/camera/frame", status_code=202)
async def camera_frame(request: Request) -> dict[str, object]:
    """
    Accept browser camera frame and process through vision/tracking/presence/attendance pipeline.
    
    Returns detection and presence information.
    """
    content_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
    if content_type != "image/jpeg":
        raise HTTPException(status_code=415, detail="Content-Type must be image/jpeg")
    
    payload = await request.body()
    try:
        frame = camera_engine.receive_frame(payload, content_type=content_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    
    # Process frame through vision engine
    detection = vision_engine.process_frame(frame)
    
    # Update presence engine with detections
    presence_snapshot = presence_engine.snapshot()
    if detection.detections:
        for det in detection.detections:
            track_id = det.get("track_id")
            confidence = det.get("confidence", 0.0)
            if track_id is not None:
                is_new_entry, status = presence_engine.update_detection(
                    track_id=track_id,
                    confidence=confidence,
                    location=None,
                    camera_id=None,
                )
    
    # Mark missed tracks for exit detection
    all_detected_track_ids = {det.get("track_id") for det in detection.detections if det.get("track_id")}
    current_presence = presence_engine.get_current_presence()
    for track_id in current_presence.keys():
        if track_id not in all_detected_track_ids:
            is_exit, exit_status = presence_engine.mark_missed(track_id)
            if is_exit:
                # Track exited, finalize attendance if applicable
                state = presence_engine.get_presence_for_track(track_id)
                if state and state.person_id:
                    attendance_engine.finalize_session(
                        person_id=state.person_id,
                        camera_id=state.camera_id,
                        location_id=None,
                        exit_time=datetime.now(timezone.utc),
                    )
    
    return {
        "accepted": True,
        "received_at": frame.received_at,
        "frames_received": camera_engine.snapshot().frames_received,
        "processing": "complete",
        **snapshot_dict(detection),
        "presence": presence_snapshot,
    }


# ============ Presence APIs (Phase 5) ============


@router.get("/api/presence/current")
def presence_current() -> dict[str, object]:
    """Get current presence state."""
    current = presence_engine.get_current_presence()
    present_people = []
    unknown_count = 0
    known_count = 0
    
    for track_id, state in current.items():
        person_info = {
            "track_id": track_id,
            "status": state.status,
            "person_id": state.person_id,
            "person_name": state.person_name,
            "location": state.location,
            "camera_id": state.camera_id,
            "first_seen_at": state.first_seen_at.isoformat() if state.first_seen_at else None,
            "last_seen_at": state.last_seen_at.isoformat() if state.last_seen_at else None,
            "confidence": round(state.confidence, 4),
        }
        present_people.append(person_info)
        
        if state.person_id:
            known_count += 1
        else:
            unknown_count += 1
    
    snapshot = presence_engine.snapshot()
    
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_present": len(present_people),
        "known_present": known_count,
        "unknown_present": unknown_count,
        "people": present_people,
        "occupancy": snapshot["present_people"],
    }


@router.get("/api/presence/person/{person_id}")
def presence_person(person_id: int) -> dict[str, object]:
    """Get presence state for a specific person."""
    state = presence_engine.get_presence_for_person(person_id)
    
    if not state:
        raise HTTPException(status_code=404, detail="Person not currently present")
    
    return {
        "status": "ok",
        "person_id": person_id,
        "track_id": state.track_id,
        "presence_status": state.status,
        "first_seen_at": state.first_seen_at.isoformat() if state.first_seen_at else None,
        "last_seen_at": state.last_seen_at.isoformat() if state.last_seen_at else None,
        "confidence": round(state.confidence, 4),
        "location": state.location,
        "camera_id": state.camera_id,
    }


# ============ Attendance APIs (Phase 5) ============


@router.get("/api/attendance/today")
def attendance_today() -> dict[str, object]:
    """Get today's attendance records."""
    records = attendance_engine.get_today_attendance()
    
    return {
        "status": "ok",
        "date": datetime.now(timezone.utc).date().isoformat(),
        "count": len(records),
        "records": records,
    }


@router.get("/api/attendance")
def attendance_list(
    person_id: int | None = None,
    location_id: int | None = None,
    status: str | None = None,
    limit: int = 100,
) -> dict[str, object]:
    """Get attendance records with optional filters."""
    records = attendance_engine.get_attendance(
        person_id=person_id,
        location_id=location_id,
        status=status,
        limit=limit,
    )
    
    return {
        "status": "ok",
        "count": len(records),
        "filters": {
            "person_id": person_id,
            "location_id": location_id,
            "status": status,
            "limit": limit,
        },
        "records": records,
    }


@router.get("/api/attendance/{attendance_id}")
def attendance_get(attendance_id: int) -> dict[str, object]:
    """Get a specific attendance record."""
    record = attendance_engine.get_attendance_by_id(attendance_id)
    
    if not record:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    
    return {
        "status": "ok",
        "record": record,
    }


@router.get("/api/attendance/person/{person_id}")
def attendance_person(person_id: int) -> dict[str, object]:
    """Get attendance records for a specific person."""
    records = attendance_engine.get_attendance(person_id=person_id, limit=50)
    
    return {
        "status": "ok",
        "person_id": person_id,
        "count": len(records),
        "records": records,
    }


@router.get("/api/attendance/stats")
def attendance_stats() -> dict[str, object]:
    """Get attendance statistics."""
    stats = attendance_engine.get_stats()
    
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **stats,
    }


# ============ Identity/People APIs (Phase 4) ============


@router.get("/api/identity/status")
def identity_status() -> dict[str, object]:
    """Identity engine status (Phase 4)."""
    return {
        "status": "ok",
        "service": "identity-engine",
        "state": "STANDBY",
        "model": "face_recognition",
        "ready": False,
        "note": "Identity engine integration pending Phase 4 completion",
    }


@router.get("/people", response_class=HTMLResponse)
def people_page(request: Request) -> HTMLResponse:
    """People/profile dashboard page."""
    try:
        with get_connection() as conn:
            people = conn.execute("SELECT id, display_name FROM persons").fetchall()
        return templates.TemplateResponse(
            request=request,
            name="people.html",
            context={"people": people or []},
        )
    except Exception:
        logger.exception("Unable to render people page")
        return templates.TemplateResponse(
            request=request,
            name="people.html",
            context={"people": []},
            status_code=503,
        )


@router.get("/attendance", response_class=HTMLResponse)
def attendance_page(request: Request) -> HTMLResponse:
    """Attendance dashboard page."""
    return templates.TemplateResponse(request=request, name="attendance.html", context={})
