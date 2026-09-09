# IntelliGate AI - AEGIS

AEGIS is a local security command center. Phase 1 provides the FastAPI application, responsive Jinja2 dashboard, project-relative configuration, and local SQLite schema. Phase 2 adds real browser camera acquisition and JPEG transport. Phase 3 adds local YOLO person detection, temporary tracking IDs, occupancy telemetry, and a live overlay.

Person detection is not face recognition and does not identify people or label anyone as criminal. Detection uses the open-source Ultralytics YOLO runtime locally; frames are not sent to a paid API or cloud service.

## Requirements

- Python 3.10 or newer (Python 3.14 is supported by the selected dependencies)
- SQLite, included with Python
- A laptop-friendly CPU is sufficient for the default `yolo11n.pt` model

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

## Phase 3 vision setup

The first processed frame lazily initializes `yolo11n.pt`. Ultralytics downloads this open-source model into its local cache when network access is available; no API key is required. Model initialization is optional: if the package, model, or download is unavailable, the camera continues working and the UI reports `Vision model unavailable`.

Tune the local runtime with environment variables: `VISION_MODEL`, `VISION_CONFIDENCE`, `VISION_INTERVAL`, `VISION_FRAME_SIZE`, and optional `OCCUPANCY_CAPACITY`. The interval is measured in received frames; skipped frames reuse the latest completed result. Temporary tracking IDs are stable only across nearby frames and are not identity.

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
- `POST /api/camera/frame` - accepts local browser JPEG frames with `Content-Type: image/jpeg` and returns the latest detection result
- `GET /api/vision/status` - latest real vision status, detections, latency, and processing rate

## Tests

```bash
python -m pytest -q
```