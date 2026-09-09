from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.engines.camera import CameraFrame
from app.engines.vision import VisionEngine
from app.main import app


JPEG = b"\xff\xd8test-frame\xff\xd9"


def test_invalid_image_handling() -> None:
    engine = VisionEngine(detector_factory=lambda _: object())
    result = engine.process_frame(CameraFrame(b"not-jpeg", "image/jpeg", None))
    assert result.status == "UNAVAILABLE"
    assert "valid JPEG" in (result.error or "")


def test_detector_initialization_failure(monkeypatch) -> None:
    monkeypatch.setattr(VisionEngine, "_decode_jpeg", staticmethod(lambda _: object()))
    engine = VisionEngine(detector_factory=lambda _: (_ for _ in ()).throw(RuntimeError("model unavailable")))
    result = engine.process_frame(CameraFrame(JPEG, "image/jpeg", None))
    assert result.status == "UNAVAILABLE"
    assert result.error == "model unavailable"


def test_empty_detection_result(monkeypatch) -> None:
    monkeypatch.setattr(VisionEngine, "_decode_jpeg", staticmethod(lambda _: object()))
    tensor = SimpleNamespace(tolist=lambda: [])
    model = lambda _: SimpleNamespace(predict=lambda **_: [SimpleNamespace(boxes=SimpleNamespace(xyxy=tensor, conf=tensor))])
    result = VisionEngine(detector_factory=model).process_frame(CameraFrame(JPEG, "image/jpeg", None))
    assert result.status == "READY"
    assert result.person_count == 0
    assert result.detections == []


def test_detection_response_schema_and_camera_frame_endpoint() -> None:
    with TestClient(app) as client:
        response = client.post("/api/camera/frame", content=JPEG, headers={"content-type": "image/jpeg"})
    body = response.json()
    assert response.status_code == 202
    assert body["accepted"] is True
    assert body["processing"] == "complete"
    assert {"person_count", "detections", "timestamp", "processing_latency_ms"}.issubset(body)
    assert isinstance(body["detections"], list)


def test_vision_status_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/api/vision/status")
    assert response.status_code == 200
    assert {"status", "person_count", "detections", "processing_latency_ms"}.issubset(response.json())