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

### 1. Database Configuration (Supabase PostgreSQL)

This application uses **Supabase Cloud PostgreSQL** as its primary relational database. No local PostgreSQL installation is required.

#### A. Obtaining Supabase Connection URI:
1. Log in to your [Supabase Dashboard](https://supabase.com/dashboard).
2. Open your project (e.g., `ayjgubyghlxiwdilgtmt`).
3. Navigate to **Project Settings** (gear icon) -> **Database**.
4. Scroll to **Connection string** and select the **URI** tab.
5. Copy the connection URI in the format:
   ```text
   postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres
   ```

#### B. Configure Environment Variables:
Copy `.env.example` to `.env` and set `DATABASE_URL`:
```bash
# In .env (do NOT commit this file to Git):
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres
```
*(Note: Never use the HTTPS API endpoint for SQLAlchemy; always use the direct `postgresql://` URI).*

#### C. Run Database Migrations:
Apply the Alembic migrations to set up all tables and indexes on Supabase:
```bash
alembic upgrade head
```

#### D. Initialize & Seed Default Fleet Data:
Seed the default camera (`CAM-01`) and the Phase 2 college fleet (`TN45BD7321`, `TN45BD8456`, `Staff Van 01`) idempotently:
```bash
py -3.13 database/init_db.py
```

---

### 2. Backend (FastAPI)
Start the FastAPI server:
```bash
py -3.13 -m uvicorn backend.app.main:app --reload --port 8000
```
- API Docs (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Check: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

### 3. Verify Database & Phase 2 Logic
Run the automated end-to-end Phase 2 test suite directly against Supabase PostgreSQL:
```bash
py -3.13 backend/test_phase2.py
```
This tests and verifies:
- College vehicle lookup & classification
- Other/visitor vehicle classification
- ENTRY & EXIT state transitions
- INSIDE & OUTSIDE status tracking
- Recognition events persistence
- Dashboard analytics summary
- College vehicle admin CRUD operations

---

### 4. AI Service (Recognition & Live Webcam)
Run the AI pipeline (YOLO26 Small + EasyOCR):
```bash
py -3.13 -m ai-service.webcam.webcam_processor
```

---

### 5. Frontend Dashboard (React + Vite)
```bash
cd frontend
npm install
npm run dev
```
- Dashboard: [http://localhost:5173](http://localhost:5173)
