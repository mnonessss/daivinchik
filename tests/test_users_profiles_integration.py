from __future__ import annotations

import pytest


async def _register(client, telegram_id: int, referral_id: int | None = None) -> dict:
    payload: dict[str, int] = {"telegram_id": telegram_id}
    if referral_id is not None:
        payload["referral_id"] = referral_id
    resp = await client.post("/users/register", json=payload)
    assert resp.status_code == 200
    return resp.json()


@pytest.mark.asyncio
async def test_user_register_is_idempotent_and_get_user_works(client):
    first = await _register(client, 930_001)
    second = await _register(client, 930_001)

    assert first["already_registered"] is False
    assert second["already_registered"] is True
    assert second["user_id"] == first["user_id"]

    get_user = await client.get(f"/users/{first['user_id']}")
    assert get_user.status_code == 200
    assert get_user.json()["telegram_id"] == 930_001


@pytest.mark.asyncio
async def test_get_unknown_user_returns_404(client):
    resp = await client.get("/users/999999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_referral_code_endpoint_returns_expected_code(client):
    registered = await _register(client, 930_010)
    user_id = registered["user_id"]

    resp = await client.get(f"/users/referral/{user_id}")
    assert resp.status_code == 200
    assert resp.json()["referral_code"] == f"ref_{user_id}"


@pytest.mark.asyncio
async def test_profile_exists_for_registered_user_and_supports_update(client):
    registered = await _register(client, 930_020)
    user_id = registered["user_id"]

    profile_resp = await client.get(f"/profiles/by-user/{user_id}")
    assert profile_resp.status_code == 200
    profile = profile_resp.json()
    profile_id = profile["id"]

    update_resp = await client.put(
        f"/profiles/{profile_id}",
        json={"name": "alice", "city": "Moscow", "age": 24, "bio": "hi"},
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["name"] == "alice"
    assert updated["city"] == "Moscow"
    assert updated["age"] == 24


@pytest.mark.asyncio
async def test_profile_update_with_empty_payload_returns_400(client):
    registered = await _register(client, 930_030)
    profile = await client.get(f"/profiles/by-user/{registered['user_id']}")
    profile_id = profile.json()["id"]

    resp = await client.put(f"/profiles/{profile_id}", json={})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_profile_photos_add_list_delete_flow(client):
    registered = await _register(client, 930_040)
    profile = await client.get(f"/profiles/by-user/{registered['user_id']}")
    profile_id = profile.json()["id"]

    add = await client.post(
        f"/profiles/{profile_id}/photos",
        json={"telegram_file_id": "photo_file_1"},
    )
    assert add.status_code == 201
    photo = add.json()
    photo_id = photo["id"]

    list_resp = await client.get(f"/profiles/{profile_id}/photos")
    assert list_resp.status_code == 200
    assert any(item["id"] == photo_id for item in list_resp.json())

    delete_resp = await client.delete(f"/profiles/{profile_id}/photos/{photo_id}")
    assert delete_resp.status_code == 204

    list_after = await client.get(f"/profiles/{profile_id}/photos")
    assert list_after.status_code == 200
    assert all(item["id"] != photo_id for item in list_after.json())


@pytest.mark.asyncio
async def test_profile_delete_removes_profile(client):
    registered = await _register(client, 930_050)
    user_id = registered["user_id"]
    profile = await client.get(f"/profiles/by-user/{user_id}")
    profile_id = profile.json()["id"]

    delete = await client.delete(f"/profiles/{profile_id}")
    assert delete.status_code == 204

    get_after = await client.get(f"/profiles/{profile_id}")
    assert get_after.status_code == 404
