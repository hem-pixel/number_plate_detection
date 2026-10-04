"""Database Initialization and Seeding Script for Supabase PostgreSQL.

This script:
1. Connects securely to Supabase PostgreSQL using DATABASE_URL from .env
2. Ensures all tables and indexes exist (via Base.metadata.create_all)
3. Seeds the default camera (CAM-01) idempotently if not present
4. Seeds predefined Phase 2 college vehicles (College Bus 01, College Bus 02, Staff Van 01) idempotently
5. Validates and displays table counts without exposing database credentials
"""

import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import inspect
from backend.app.database.connection import engine, SessionLocal
from backend.app.database.base import Base
# Import all models
from backend.app.models import Camera, CollegeVehicle, Vehicle, RecognitionEvent  # noqa: F401
from backend.app.services.camera_service import CameraService
from backend.app.services.college_vehicle_service import CollegeVehicleService


def init_database(seed: bool = True) -> bool:
    print("=" * 65)
    print("SUPABASE POSTGRESQL INITIALIZATION & SEEDING")
    print("=" * 65)

    # 1. Connection check with masked credentials
    masked_url = engine.url.render_as_string(hide_password=True)
    print(f"Target Database: {masked_url}")

    try:
        with engine.connect() as conn:
            pass
        print("-> Connection test: SUCCESS (Connected to Supabase PostgreSQL)")
    except Exception as e:
        print(f"-> Connection test: FAILED - {e}")
        return False

    # 2. Idempotent Schema Creation
    print("\nEnsuring database tables and indexes exist...")
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    print(f"-> Active Tables: {', '.join(sorted(existing_tables))}")

    # 3. Seed Default Camera & College Vehicles
    if seed:
        print("\nSeeding initial data idempotently...")
        with SessionLocal() as db:
            # Seed Default Camera
            cam_service = CameraService(db)
            cam = cam_service.seed_default_camera()
            print(f"-> Default Camera verified: {cam.camera_code} ({cam.camera_name})")

            # Seed College Vehicles (Phase 2 Demo Fleet)
            college_service = CollegeVehicleService(db)
            college_service.seed_default_college_vehicles()

            vehicles, total = college_service.list_college_vehicles()
            print(f"-> Registered College Vehicles ({total} total):")
            for v in vehicles:
                print(f"   * {v.vehicle_number} | {v.vehicle_name} ({v.vehicle_type}) | Status: {v.status} | Current: {v.current_status}")

    print("\n" + "=" * 65)
    print("DATABASE INITIALIZATION COMPLETED SUCCESSFULLY!")
    print("=" * 65)
    return True


if __name__ == "__main__":
    success = init_database(seed=True)
    if not success:
        sys.exit(1)
