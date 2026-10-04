import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger("database")


def get_database_url() -> str:
    """Validates and formats the database URL from settings/environment."""
    raw_url = settings.DATABASE_URL.strip() if settings.DATABASE_URL else ""

    if not raw_url:
        raise ValueError(
            "DATABASE_URL environment variable is missing or empty! "
            "Please configure your Supabase PostgreSQL connection string in .env: "
            "DATABASE_URL=postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres "
            "(Automatic fallback to SQLite has been removed)."
        )

    # Catch accidental HTTP/HTTPS Supabase API URLs copied from dashboard
    if raw_url.startswith("https://") or raw_url.startswith("http://"):
        raise ValueError(
            f"Invalid DATABASE_URL protocol: '{raw_url[:8]}...'. "
            "A Supabase HTTPS API URL was provided instead of the PostgreSQL connection URI. "
            "Please use the direct PostgreSQL URI in the format: "
            "postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres "
            "found in Supabase Settings -> Database -> Connection string -> URI."
        )

    # Disallow SQLite unless explicitly in testing mode
    is_test_env = (
        getattr(settings, "TESTING", False)
        or os.getenv("TESTING", "").lower() in ("true", "1", "yes")
        or "pytest" in sys.modules
    )
    if "sqlite" in raw_url and not is_test_env:
        raise ValueError(
            "SQLite database is not permitted for normal application execution. "
            "Please configure the Supabase PostgreSQL connection string in .env "
            "or set TESTING=true if running isolated automated tests."
        )

    # Convert postgresql:// to postgresql+psycopg2:// for SQLAlchemy
    if raw_url.startswith("postgresql://") and not raw_url.startswith("postgresql+psycopg2://"):
        raw_url = raw_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    return raw_url


def create_db_engine():
    """Creates the SQLAlchemy Engine with production connection pooling for Supabase."""
    db_url = get_database_url()

    if "sqlite" in db_url:
        eng = create_engine(
            db_url,
            connect_args={"check_same_thread": False},
            echo=False
        )
        logger.info("Using SQLite database for isolated test execution.")
        return eng

    eng = create_engine(
        db_url,
        pool_pre_ping=True,      # Validates connections before checkout to avoid stale socket errors
        pool_recycle=300,        # Recycles connections after 5 minutes (Supabase cloud timeout protection)
        pool_size=10,
        max_overflow=20,
        echo=False
    )

    # Verify connectivity immediately without leaking credentials in logs
    masked_url = eng.url.render_as_string(hide_password=True)
    try:
        with eng.connect() as conn:
            pass
        logger.info(f"Connected to Supabase PostgreSQL database: {masked_url}")
    except Exception as e:
        logger.error(f"Failed to connect to Supabase PostgreSQL database ({masked_url}): {e}")
        raise RuntimeError(
            f"Could not connect to database at {masked_url}. "
            "Please verify that your Supabase database is active, network is reachable, "
            "and credentials in .env are correct."
        ) from e

    return eng


engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
