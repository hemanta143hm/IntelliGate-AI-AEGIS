from fastapi.testclient import TestClient

from app.engines.camera import CameraEngine, CameraStatus
from app.main import app


def test_camera_service_import_and_status_model() -> None:
    engine = CameraEngine()
    assert engine.snapshot().status is CameraStatus.OFFLINE
    engine.set_status(CameraStatus.REQUESTING)
    assert engine.snapshot().status is CameraStatus.REQUESTING
    assert {status.value for status in CameraStatus} == {
        "OFFLINE",
        "REQUESTING",
        "ONLINE",
        "ERROR",
        "STOPPED",
    }


def test_camera_test_api_health() -> None:
    with TestClient(app) as client:
        response = client.get("/api/camera/test")
    assert response.status_code == 200
    assert response.json()["service"] == "camera-engine"
    assert response.json()["ready_for_browser_frames"] is True


def test_camera_frame_endpoint_validation() -> None:
    with TestClient(app) as client:
        missing_type = client.post("/api/camera/frame", content=b"frame")
        invalid_jpeg = client.post(
            "/api/camera/frame",
            content=b"not-a-jpeg",
            headers={"content-type": "image/jpeg"},
        )
        accepted = client.post(
            "/api/camera/frame",
            content=b"\xff\xd8local-frame\xff\xd9",
            headers={"content-type": "image/jpeg"},
        )

    assert missing_type.status_code == 415
    assert invalid_jpeg.status_code == 422
    assert accepted.status_code == 202
    assert accepted.json()["accepted"] is True
