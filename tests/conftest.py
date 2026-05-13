"""
Integration test setup.

Import order matters: set env and Celery eager mode before loading the FastAPI app,
so `database` and Celery tasks use the test configuration.
"""

from __future__ import annotations

import asyncio
import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")
os.environ.setdefault("CELERY_BROKER_URL", "memory://")
os.environ.setdefault("CELERY_RESULT_BACKEND", "cache+memory://")

from celery_app import celery_app

celery_app.conf.update(
    task_always_eager=True,
    task_eager_propagates=True,
)

from httpx import ASGITransport, AsyncClient
import pytest

from database import engine
from main import app
from models import Base


@pytest.fixture(scope="session")
def engine_setup():
    async def create_schema():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_schema():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    asyncio.run(create_schema())
    yield
    asyncio.run(drop_schema())


class _InMemoryAsyncRedis:
    """Minimal async Redis subset used by ranking feed cache (tests only)."""

    def __init__(self):
        self._kv: dict[str, str] = {}
        self._lists: dict[str, list[str]] = {}

    async def get(self, key: str):
        return self._kv.get(key)

    async def set(self, key: str, value: str, ex: int | None = None):
        self._kv[key] = value

    async def delete(self, *keys: str):
        for key in keys:
            self._kv.pop(key, None)
            self._lists.pop(key, None)

    async def rpush(self, key: str, *values: str):
        lst = self._lists.setdefault(key, [])
        lst.extend(values)

    async def lpop(self, key: str):
        lst = self._lists.get(key)
        if not lst:
            return None
        return lst.pop(0)

    async def llen(self, key: str):
        return len(self._lists.get(key, []))

    async def expire(self, key: str, seconds: int):
        return True


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    fake = _InMemoryAsyncRedis()
    monkeypatch.setattr("ranking.service.redis_client", fake)
    yield


@pytest.fixture
async def client(engine_setup):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
