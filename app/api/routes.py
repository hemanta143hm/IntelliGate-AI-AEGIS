"""API and dashboard routes."""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.health import get_health, get_system_status
from app.engines.camera import camera_engine
from app.engines.vision import snapshot_dict, vision_engine

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).resolve().parents[2] / "frontend" / "templates")


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request) -> HTMLResponse:
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
    return get_health()


@router.get("/api/system/status")
def system_status() -> dict[str, object]:
    return get_system_status()


@router.get("/camera", response_class=HTMLResponse)
def camera_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="camera.html", context={})


@router.get("/api/camera/test")
def camera_test() -> dict[str, object]:
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
    return snapshot_dict(vision_engine.snapshot())


@router.post("/api/camera/frame", status_code=202)
async def camera_frame(request: Request) -> dict[str, object]:
    content_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
    if content_type != "image/jpeg":
        raise HTTPException(status_code=415, detail="Content-Type must be image/jpeg")
    payload = await request.body()
    try:
        frame = camera_engine.receive_frame(payload, content_type=content_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    detection = vision_engine.process_frame(frame)
    return {
        "accepted": True,
        "received_at": frame.received_at,
        "frames_received": camera_engine.snapshot().frames_received,
        "processing": "complete",
        **snapshot_dict(detection),
    }
