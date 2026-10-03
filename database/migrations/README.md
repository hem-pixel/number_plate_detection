# Database Migrations

This folder manages PostgreSQL database migrations using Alembic and SQLAlchemy.

## Setting Up Migrations
To initialize and run migrations on local PostgreSQL:

```bash
# Initialize migration environment (if not already done)
alembic revision --autogenerate -m "Initial tables"

# Apply migrations
alembic upgrade head
```
