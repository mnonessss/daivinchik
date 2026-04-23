from datetime import datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Interactions, Users
from ranking.service import recalculate_user_ranking, warmup_feed_cache


async def create_interaction(db, from_user, to_user, action):
    from_exists = (
        await db.execute(select(Users.id).where(Users.id == from_user))
    ).scalar_one_or_none()
    to_exists = (
        await db.execute(select(Users.id).where(Users.id == to_user))
    ).scalar_one_or_none()
    if not from_exists or not to_exists:
        raise ValueError("Both users must exist before creating interaction")

    interaction = Interactions(
        from_user=from_user,
        to_user=to_user,
        action=action,
        created_at=datetime.now(),
    )
    db.add(interaction)
    await db.commit()
    await db.refresh(interaction)

    for user_id in {from_user, to_user}:
        await recalculate_user_ranking(db, user_id)
        await warmup_feed_cache(db, user_id)
    return interaction


async def has_mutual_like(db: AsyncSession, user_a: int, user_b: int) -> bool:
    like_a_to_b = (
        await db.execute(
            select(Interactions.id).where(
                and_(
                    Interactions.from_user == user_a,
                    Interactions.to_user == user_b,
                    Interactions.action == "like",
                )
            )
        )
    ).scalar_one_or_none()
    if not like_a_to_b:
        return False

    like_b_to_a = (
        await db.execute(
            select(Interactions.id).where(
                and_(
                    Interactions.from_user == user_b,
                    Interactions.to_user == user_a,
                    Interactions.action == "like",
                )
            )
        )
    ).scalar_one_or_none()
    return like_b_to_a is not None
