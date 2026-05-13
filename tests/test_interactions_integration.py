from __future__ import annotations

import pytest


async def _register(client, telegram_id: int) -> int:
    resp = await client.post("/users/register", json={"telegram_id": telegram_id})
    assert resp.status_code == 200
    return resp.json()["user_id"]


@pytest.mark.asyncio
async def test_like_creates_interaction_and_match_is_false_initially(client):
    user_a = await _register(client, 920_001)
    user_b = await _register(client, 920_002)

    like_resp = await client.post(
        "/interactions/",
        json={"from_user": user_a, "to_user": user_b, "action": "like"},
    )
    assert like_resp.status_code == 201
    body = like_resp.json()
    assert body["action"] == "like"
    assert body["from_user"] == user_a
    assert body["to_user"] == user_b

    match_resp = await client.get(f"/interactions/match/{user_a}/{user_b}")
    assert match_resp.status_code == 200
    assert match_resp.json()["matched"] is False


@pytest.mark.asyncio
async def test_mutual_likes_create_match(client):
    user_a = await _register(client, 920_010)
    user_b = await _register(client, 920_011)

    await client.post(
        "/interactions/",
        json={"from_user": user_a, "to_user": user_b, "action": "like"},
    )
    second_like = await client.post(
        "/interactions/",
        json={"from_user": user_b, "to_user": user_a, "action": "like"},
    )
    assert second_like.status_code == 201

    match_resp = await client.get(f"/interactions/match/{user_a}/{user_b}")
    assert match_resp.status_code == 200
    assert match_resp.json()["matched"] is True


@pytest.mark.asyncio
async def test_skip_and_dialog_start_are_accepted(client):
    user_a = await _register(client, 920_020)
    user_b = await _register(client, 920_021)

    skip_resp = await client.post(
        "/interactions/",
        json={"from_user": user_a, "to_user": user_b, "action": "skip"},
    )
    assert skip_resp.status_code == 201
    assert skip_resp.json()["action"] == "skip"

    dialog_resp = await client.post(
        "/interactions/",
        json={"from_user": user_a, "to_user": user_b, "action": "dialog_start"},
    )
    assert dialog_resp.status_code == 201
    assert dialog_resp.json()["action"] == "dialog_start"


@pytest.mark.asyncio
async def test_interaction_with_unknown_users_returns_400(client):
    resp = await client.post(
        "/interactions/",
        json={"from_user": 999_000, "to_user": 999_001, "action": "like"},
    )
    assert resp.status_code == 400
    assert "Both users must exist" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_invalid_interaction_action_returns_422(client):
    user_a = await _register(client, 920_030)
    user_b = await _register(client, 920_031)

    resp = await client.post(
        "/interactions/",
        json={"from_user": user_a, "to_user": user_b, "action": "super_like"},
    )
    assert resp.status_code == 422
