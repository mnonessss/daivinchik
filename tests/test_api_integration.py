from __future__ import annotations

import pytest
from sqlalchemy import select

from database import async_session_maker
from models import Ranking, Users


@pytest.mark.asyncio
async def test_register_with_referral_persisted_in_db(client):
    ref = await client.post("/users/register", json={"telegram_id": 910_001})
    assert ref.status_code == 200
    referrer_id = ref.json()["user_id"]

    invited = await client.post(
        "/users/register",
        json={"telegram_id": 910_002, "referral_id": referrer_id},
    )
    assert invited.status_code == 200
    assert invited.json()["already_registered"] is False

    async with async_session_maker() as db:
        row = await db.execute(select(Users).where(Users.telegram_id == 910_002))
        user = row.scalar_one()
        assert user.referral_id == referrer_id


@pytest.mark.asyncio
async def test_register_with_invalid_referral_id_stored_as_null(client):
    resp = await client.post(
        "/users/register",
        json={"telegram_id": 910_003, "referral_id": 999_999},
    )
    assert resp.status_code == 200

    async with async_session_maker() as db:
        row = await db.execute(select(Users).where(Users.telegram_id == 910_003))
        user = row.scalar_one()
        assert user.referral_id is None


@pytest.mark.asyncio
async def test_ranking_recalculate_async_eager_updates_ranking_row(client):
    reg = await client.post("/users/register", json={"telegram_id": 910_010})
    assert reg.status_code == 200
    user_id = reg.json()["user_id"]

    async_resp = await client.post(f"/ranking/recalculate/{user_id}/async")
    assert async_resp.status_code == 200
    body = async_resp.json()
    assert body["status"] == "queued"
    assert body.get("task_id")

    async with async_session_maker() as db:
        row = await db.execute(select(Ranking).where(Ranking.user_id == user_id))
        ranking = row.scalar_one_or_none()
        assert ranking is not None
        assert ranking.final_score is not None

    get_resp = await client.get(f"/ranking/{user_id}")
    assert get_resp.status_code == 200
    assert "final_score" in get_resp.json()


@pytest.mark.asyncio
async def test_ranking_recalculate_all_async_eager(client):
    await client.post("/users/register", json={"telegram_id": 910_020})

    async_resp = await client.post("/ranking/recalculate-all/async")
    assert async_resp.status_code == 200
    assert async_resp.json()["status"] == "queued"
