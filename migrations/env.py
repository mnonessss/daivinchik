import os
from logging.config import fileConfig
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

from alembic import context

from models import Base

load_dotenv()

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_sync_database_url() -> str:
    """Sync URL for Alembic (postgresql+psycopg2). Matches database.py env logic."""
    explicit = os.getenv("DATABASE_URL")
    if explicit:
        if explicit.startswith("sqlite"):
            return explicit.replace("sqlite+aiosqlite://", "sqlite://")
        if explicit.startswith("postgresql+asyncpg://"):
            return explicit.replace(
                "postgresql+asyncpg://", "postgresql+psycopg2://", 1
            )
        return explicit

    user = os.getenv("USER_DB")
    pwd = os.getenv("PWD_DB")
    db_name = os.getenv("DB_NAME")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    if not user or not pwd or not db_name:
        raise RuntimeError(
            "Alembic: set DATABASE_URL or USER_DB, PWD_DB, DB_NAME (and DB_HOST, DB_PORT)"
        )
    return (
        f"postgresql+psycopg2://{quote_plus(user)}:{quote_plus(pwd)}"
        f"@{host}:{port}/{quote_plus(db_name)}"
    )


def run_migrations_offline() -> None:
    url = get_sync_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = get_sync_database_url()
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = url
    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
