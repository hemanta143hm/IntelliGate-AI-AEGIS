from fastapi.testclient import TestClient

from app.main import app


def test_application_import_and_routes() -> None:
    with TestClient(app) as client:
        assert client.get("/").status_code == 200
        assert client.get("/health").json()["status"] == "ok"
        assert client.get("/api/system/status").status_code == 200
