from datetime import datetime
from sqlalchemy import select

from models import Users


async def create_user(db, telegram_id, referral_id: int | None = None):
    user = Users(
            telegram_id=telegram_id,
            referral_id=referral_id,
        )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_user_by_telegram_id(db, telegram_id):
    query = await db.execute(select(Users).where(Users.telegram_id == telegram_id))
    return query.scalar_one_or_none()


async def get_user_by_id(db, user_id: int):
    return await db.get(Users, user_id)


async def update_user_last_active(db, user_id):
    user = await db.get(Users, user_id)
    user.last_active = datetime.now()
    await db.commit()
