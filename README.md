# Indian Vehicle Number Plate Recognition - Full-Stack Localhost System

A complete full-stack application for real-time Indian Vehicle Number Plate Recognition (ANPR/ALPR) running entirely on **Localhost (Windows)**.

---

## Architecture Overview

```
                    LOCALHOST
                       │
                       ▼
              React Frontend (:5173)
                       │
                REST / WebSocket
                       │
                       ▼
              FastAPI Backend (:8000)
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
     AI Processing              PostgreSQL (:5432)
          │                         │
          ▼                         │
 YOLO + OCR + Validation            │
          │                         │
          └────────────┬────────────┘
                       ▼
              Stored Recognition
          (Full Frame & Plate Crop)
                       │
                       ▼
              Frontend Dashboard
```

---

## Project Structure

```
number-plate-recognition/
├── frontend/                 # React + Vite web dashboard (Port 5173)
│   ├── src/
│   │   ├── components/       # UI components (Recent Recognitions, Detail Modal)
│   │   ├── pages/            # Dashboard, Live Camera, History, Cameras
│   │   ├── services/         # Axios / Fetch API & WebSocket client
│   │   └── hooks/            # Custom React hooks
│   ├── package.json
│   └── vite.config.js
│
├── backend/                  # FastAPI REST API & WebSocket server (Port 8000)
│   ├── app/
│   │   ├── api/routes/       # Endpoints: health, recognitions, cameras, vehicles
│   │   ├── core/             # Configuration & logging
│   │   ├── database/         # SQLAlchemy connection & Base
│   │   ├── models/           # RecognitionEvent, Camera models
│   │   ├── schemas/          # Pydantic request/response models
│   │   ├── services/         # RecognitionService, ImageService, CameraService
│   │   └── main.py           # FastAPI entrypoint & static mounts
│   └── requirements.txt
│
├── ai-service/               # Modular AI Pipeline
│   ├── models/               # best.pt (YOLO26 Small)
│   ├── detection/            # PlateDetector (YOLO)
│   ├── ocr/                  # PlateOCR (EasyOCR + allowlist)
│   ├── preprocessing/        # ImagePreprocessor (contrast, CLAHE, Otsu)
│   ├── validation/           # PlateValidator (Indian format regex & heuristics)
│   ├── tracking/             # PlateTracker & VehicleEventManager
│   ├── pipeline/             # RecognitionPipeline (unified frame-to-result)
│   └── webcam/               # WebcamProcessor (live camera capture & runner)
│
├── storage/                  # Local filesystem storage
│   ├── vehicles/             # Full vehicle capture frames
│   └── plates/               # Cropped license plate images
│
├── database/                 # Schema & Migrations
│   ├── schema/schema.sql     # PostgreSQL DDL tables & indexes
│   └── migrations/           # Alembic migration scripts
│
├── tests/                    # Pipeline & API unit tests
├── .env.example              # Environment variables template
├── .env                      # Localhost configuration
├── docker-compose.yml        # PostgreSQL container
└── README.md
```

---

## Localhost Quickstart

### 1. Database (PostgreSQL)
Start PostgreSQL using Docker:
```bash
docker-compose up -d postgres
```
*Or use local PostgreSQL service on `localhost:5432` with database `number_plate_db`.*

### 2. Backend (FastAPI)
```bash
uvicorn backend.app.main:app --reload --port 8000
```
- Swagger Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### 3. AI Service (Recognition & Webcam)
```bash
python -m ai_service.webcam.webcam_processor
```

### 4. Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev
```
- Dashboard: [http://localhost:5173](http://localhost:5173)
