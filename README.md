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

## Endpoints

- `GET /` - security command-center dashboard
- `GET /health` - database, storage, and application health
- `GET /api/system/status` - persisted system metrics and engine readiness

## Tests

```bash
python -m pytest -q
```