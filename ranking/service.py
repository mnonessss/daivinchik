import json
from datetime import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Interactions, Profiles, Ranking, Users
from redis_client import redis_client

FEED_CHUNK_SIZE = 10
FEED_CACHE_TTL_SECONDS = 300


def feed_queue_key(user_id):
    return f"feed:queue:{user_id}"


def feed_offset_key(user_id):
    return f"feed:offset:{user_id}"


def primary_score(profile):
    # Level 1: анкета + полнота + фото + первичные предпочтения
    base_fields = [profile.age, profile.gender, profile.city, profile.bio]
    completeness = sum(1 for value in base_fields if value) / len(base_fields)
    photo_factor = min(profile.photos_count / 5, 1.0)
    preference_fields = [
        profile.preferred_age_min,
        profile.preferred_age_max,
        profile.preferred_gender,
        profile.preferred_city,
    ]
    preference_factor = (
        sum(1 for value in preference_fields if value is not None and value != "")
        / len(preference_fields)
    )
    return round((completeness * 0.5 + photo_factor * 0.2 + preference_factor * 0.3) * 100, 2)


async def behavioral_score(db, user_id):
    # Level 2: лайки, like/skip ratio, мэтчи, диалоги, активность по времени
    likes = (
        await db.execute(
            select(func.count(Interactions.id)).where(
                and_(Interactions.to_user == user_id, Interactions.action == "like")
            )
        )
    ).scalar_one()
    skips = (
        await db.execute(
            select(func.count(Interactions.id)).where(
                and_(Interactions.to_user == user_id, Interactions.action == "skip")
            )
        )
    ).scalar_one()
    dialogs_started = (
        await db.execute(
            select(func.count(Interactions.id)).where(
                and_(Interactions.from_user == user_id, Interactions.action == "dialog_start")
            )
        )
    ).scalar_one()
    outgoing_likes = set(
        (
            await db.execute(
                select(Interactions.to_user).where(
                    and_(Interactions.from_user == user_id, Interactions.action == "like")
                )
            )
        ).scalars()
    )
    incoming_likes = set(
        (
            await db.execute(
                select(Interactions.from_user).where(
                    and_(Interactions.to_user == user_id, Interactions.action == "like")
                )
            )
        ).scalars()
    )
    matches = len(outgoing_likes.intersection(incoming_likes))
    evening_activity = (
        await db.execute(
            select(func.count(Interactions.id)).where(
                and_(
                    Interactions.from_user == user_id,
                    func.extract("hour", Interactions.created_at) >= 18,
                    func.extract("hour", Interactions.created_at) <= 23,
                )
            )
        )
    ).scalar_one()
    all_activity = (
        await db.execute(select(func.count(Interactions.id)).where(Interactions.from_user == user_id))
    ).scalar_one()

    likes_component = min(likes / 50, 1.0)
    ratio_component = min(likes / max(skips, 1), 1.0)
    match_component = min(matches / max(len(incoming_likes), 1), 1.0)
    dialog_component = min(dialogs_started / max(matches, 1), 1.0)
    time_component = min(evening_activity / max(all_activity, 1), 1.0)

    return round(
        (
            likes_component * 0.3
            + ratio_component * 0.2
            + match_component * 0.2
            + dialog_component * 0.2
            + time_component * 0.1
        )
        * 100,
        2,
    )


async def referral_bonus(db, user_id):
    # Level 3 extra factor: рефералы
    invited_count = (
        await db.execute(select(func.count(Users.id)).where(Users.referral_id == user_id))
    ).scalar_one()
    return round(min(invited_count / 10, 1.0) * 10, 2)


async def recalculate_user_ranking(db, user_id):
    profile = (
        await db.execute(select(Profiles).where(Profiles.user_id == user_id))
    ).scalar_one_or_none()
    if not profile:
        return None

    primary = primary_score(profile)
    behavioral = await behavioral_score(db, user_id)
    referral_bonus_score = await referral_bonus(db, user_id)
    final = round(primary * 0.55 + behavioral * 0.40 + referral_bonus_score * 0.05, 2)

    ranking_obj = (
        await db.execute(select(Ranking).where(Ranking.user_id == user_id))
    ).scalar_one_or_none()
    if not ranking_obj:
        ranking_obj = Ranking(user_id=user_id)
        db.add(ranking_obj)

    ranking_obj.primary_score = primary
    ranking_obj.behavioral_score = behavioral
    ranking_obj.final_score = final
    ranking_obj.updated_at = datetime.now()
    await db.commit()
    await db.refresh(ranking_obj)
    return ranking_obj


async def get_user_ranking(db, user_id):
    ranking_obj = (
        await db.execute(select(Ranking).where(Ranking.user_id == user_id))
    ).scalar_one_or_none()
    if ranking_obj:
        return ranking_obj
    return await recalculate_user_ranking(db, user_id)


async def get_ranked_candidates(db, user_id):
    viewer = (
        await db.execute(select(Profiles).where(Profiles.user_id == user_id))
    ).scalar_one_or_none()
    if not viewer:
        return []

    interacted_user_ids = set(
        (
            await db.execute(
                select(Interactions.to_user).where(
                    and_(
                        Interactions.from_user == user_id,
                        Interactions.action.in_(("like", "skip")),
                    )
                )
            )
        ).scalars()
    )

    filters = [Profiles.user_id != user_id]
    if interacted_user_ids:
        filters.append(~Profiles.user_id.in_(interacted_user_ids))
    if viewer.preferred_gender:
        filters.append(
            or_(Profiles.gender.is_(None), Profiles.gender == viewer.preferred_gender)
        )
    if viewer.preferred_city:
        filters.append(
            or_(Profiles.city.is_(None), Profiles.city == viewer.preferred_city)
        )
    if viewer.preferred_age_min is not None:
        filters.append(
            or_(Profiles.age.is_(None), Profiles.age >= viewer.preferred_age_min)
        )
    if viewer.preferred_age_max is not None:
        filters.append(
            or_(Profiles.age.is_(None), Profiles.age <= viewer.preferred_age_max)
        )

    candidates = (await db.execute(select(Profiles).where(and_(*filters)))).scalars().all()
    payload: list[dict] = []
    for candidate in candidates:
        candidate_ranking = await get_user_ranking(db, candidate.user_id)
        if not candidate_ranking:
            continue
        payload.append(
            {
                "profile_id": candidate.id,
                "user_id": candidate.user_id,
                "name": candidate.name,
                "age": candidate.age,
                "gender": candidate.gender,
                "city": candidate.city,
                "bio": candidate.bio,
                "final_score": candidate_ranking.final_score,
            }
        )
    payload.sort(key=lambda item: item["final_score"], reverse=True)
    return payload


async def load_next_chunk(db, user_id):
    ranked = await get_ranked_candidates(db, user_id)
    if not ranked:
        return 0

    offset_key = feed_offset_key(user_id)
    queue_key = feed_queue_key(user_id)
    offset_raw = await redis_client.get(offset_key)
    offset = int(offset_raw) if offset_raw is not None else 0

    if offset >= len(ranked):
        offset = 0

    chunk = ranked[offset : offset + FEED_CHUNK_SIZE]
    if not chunk:
        offset = 0
        chunk = ranked[:FEED_CHUNK_SIZE]

    await redis_client.delete(queue_key)
    await redis_client.rpush(queue_key, *[json.dumps(item) for item in chunk])
    await redis_client.expire(queue_key, FEED_CACHE_TTL_SECONDS)

    new_offset = offset + len(chunk)
    if new_offset >= len(ranked):
        new_offset = 0
    await redis_client.set(offset_key, str(new_offset), ex=FEED_CACHE_TTL_SECONDS)
    return len(chunk)


async def warmup_feed_cache(db, user_id):
    try:
        loaded = await load_next_chunk(db, user_id)
        return loaded > 0
    except Exception:
        ranked = await get_ranked_candidates(db, user_id)
        return len(ranked) > 0


async def get_next_profile_from_feed(db, user_id):
    try:
        queue_key = feed_queue_key(user_id)
        item = await redis_client.lpop(queue_key)
        if not item:
            loaded = await load_next_chunk(db, user_id)
            if loaded == 0:
                return None
            item = await redis_client.lpop(queue_key)
            if not item:
                return None

        if await redis_client.llen(queue_key) == 0:
            await load_next_chunk(db, user_id)
        return json.loads(item)
    except Exception:
        ranked = await get_ranked_candidates(db, user_id)
        if not ranked:
            return None
        return ranked[0]
