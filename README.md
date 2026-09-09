# IntelliGate AI - AEGIS

AEGIS is a security command-center foundation. Phase 1 provides a FastAPI application, a responsive Jinja2 dashboard, project-relative configuration, and a local SQLite schema for people, locations, cameras, zones, attendance, events, incidents, and audit logs.

The application does not generate or imply AI detections. The AI engines are explicitly shown as `STANDBY` until their real implementations are added.

## Requirements

- Python 3.10 or newer (Python 3.14 is supported by the selected dependencies)
- SQLite, included with Python

## Run on Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python run.py
```

## Run on Windows

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python run.py
```

Open `http://127.0.0.1:8000/`. The database is created automatically at `data/aegis.sqlite3` on startup. Override settings with environment variables or a local `.env` file based on `.env.example`.

## Test the real laptop webcam in a Codespace

1. Start AEGIS inside the Codespace with `python run.py`. The server listens on `0.0.0.0:8000` so the forwarded port can reach it.
2. In the VS Code **Ports** panel, forward port `8000` and open its HTTPS browser link. Use that forwarded HTTPS URL, not a plain HTTP container URL: camera access requires a secure context.
3. Open **Live camera**, select a listed video input, and click **Start camera**. Approve the browser permission prompt. The page uses the browser's laptop webcam through `navigator.mediaDevices`; it does not select a camera by numeric index.
4. Confirm the live preview, resolution, FPS estimate, and `Backend connected` state. The page sends a lightweight JPEG frame to `POST /api/camera/frame` every two seconds. **Snapshot** saves a local JPEG from the preview.
5. To test failures, deny permission, disconnect the webcam, or stop the server and verify the visible `DENIED`, `ERROR`, or `Backend unavailable` state. Restart the camera after reconnecting a device.

Frames are processed by the local AEGIS application and are not intentionally uploaded to third-party services. No cloud AI or external camera is required.

## Endpoints

- `GET /` - security command-center dashboard
- `GET /health` - database, storage, and application health
- `GET /api/system/status` - persisted system metrics and engine readiness
- `GET /camera` - live browser camera page
- `GET /api/camera/test` - camera engine readiness and receive counters
- `POST /api/camera/frame` - accepts local browser JPEG frames with `Content-Type: image/jpeg`

## Tests

```bash
python -m pytest -q
```