from sqlalchemy import create_engine

from app.core.config import get_settings


settings = get_settings()

database_url = settings.database_url
# Automatically adapt standard postgresql:// or postgres:// to postgresql+psycopg://
if database_url.startswith("postgresql://") or database_url.startswith("postgres://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)

connect_args = {}
engine_kwargs = {
    "pool_pre_ping": True,
}

if database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False
else:
    # Recommended settings for serverless / cloud PostgreSQL (Supabase pooler)
    engine_kwargs["pool_recycle"] = 300

engine = create_engine(
    database_url,
    connect_args=connect_args,
    **engine_kwargs,
)