"""API and dashboard routes."""

import logging
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.health import get_health, get_system_status

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
