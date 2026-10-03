# Number Plate Recognition - Backend Service

FastAPI REST & WebSocket backend for the Indian Vehicle Number Plate Recognition application.

## Features
- **FastAPI** high performance REST API + WebSocket broadcaster.
- **PostgreSQL** persistence with SQLAlchemy ORM.
- **Local Storage Management**: Saves full vehicle frames and cropped plate images.
- **Real-Time WebSocket**: Broadcasts recognition events instantly to connected frontend dashboards.

## Localhost Running (Port 8000)

```bash
uvicorn backend.app.main:app --reload --port 8000
```

- API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- WebSocket Endpoint: `ws://localhost:8000/ws`
- Static Storage: `http://localhost:8000/storage/`
