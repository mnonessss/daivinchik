import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")
    USER_DB = os.getenv("USER_DB")
    PWD_DB = os.getenv("PWD_DB")
    DB_NAME = os.getenv("DB_NAME")

    if not USER_DB or not PWD_DB or not DB_NAME:
        raise RuntimeError("USER_DB, PWD_DB and DB_NAME must be set in environment/.env")

    DATABASE_URL = (
        f"postgresql+asyncpg://{USER_DB}:{PWD_DB}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

_engine_kwargs: dict = {"echo": False}
if DATABASE_URL.startswith("sqlite"):
    from sqlalchemy.pool import StaticPool

    _engine_kwargs.update(
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
else:
    _engine_kwargs.update(
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )

engine = create_async_engine(DATABASE_URL, **_engine_kwargs)


async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def get_db():
    async with async_session_maker() as session:
        yield session
