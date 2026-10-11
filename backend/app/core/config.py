import os
from pathlib import Path
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic_settings import BaseSettings
else:
    try:
        from pydantic_settings import BaseSettings
    except ImportError:
        from pydantic import BaseModel as BaseSettings


from dotenv import load_dotenv

# Project Root Directory
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Load environment variables from project root .env
load_dotenv(PROJECT_ROOT / ".env")


class Settings(BaseSettings):
    PROJECT_NAME: str = "Indian Vehicle Number Plate Recognition"
    API_V1_STR: str = "/api/v1"
    PROJECT_ROOT: Path = PROJECT_ROOT

    # Database: Supabase PostgreSQL (or test SQLite if explicitly configured for tests)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    TESTING: bool = os.getenv("TESTING", "false").lower() in ("true", "1", "yes")

    # Storage Paths
    STORAGE_DIR: Path = PROJECT_ROOT / os.getenv("STORAGE_DIR", "storage")
    VEHICLES_DIR: Path = PROJECT_ROOT / os.getenv("VEHICLES_DIR", "storage/vehicles")
    PLATES_DIR: Path = PROJECT_ROOT / os.getenv("PLATES_DIR", "storage/plates")

    # Cooldown & Deduplication
    EVENT_COOLDOWN_SECONDS: float = float(os.getenv("EVENT_COOLDOWN_SECONDS", "10.0"))

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*"
    ]

    # Security & Authentication (Phase 5)
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "np-secure-auth-jwt-secret-phase5-2026-token-key-x99")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    AI_SERVICE_API_KEY: str = os.getenv("AI_SERVICE_API_KEY", "ai-m2m-gate-cam-secure-api-key-2026")
    LOGIN_RATE_LIMIT_MAX_ATTEMPTS: int = int(os.getenv("LOGIN_RATE_LIMIT_MAX_ATTEMPTS", "5"))
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = int(os.getenv("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "60"))

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
