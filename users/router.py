from fastapi import APIRouter, Depends
from pydantic import BaseModel

from database import get_db
from profiles.schema import ProfileCreate
from profiles.service import create_profile, get_profile_by_user_id
from users.service import (
        create_user,
        get_user_by_telegram_id,
        update_user_last_active
    )

router = APIRouter(prefix="/users", tags=["Users"])


class RegisterBody(BaseModel):
    telegram_id: int


@router.post("/register")
async def register_user(body: RegisterBody, db=Depends(get_db)):
    user = await get_user_by_telegram_id(db, body.telegram_id)
    if user:
        await update_user_last_active(db, user.id)
        profile = await get_profile_by_user_id(db, user.id)
        if not profile:
            await create_profile(
                db,
                ProfileCreate(
                    user_id=user.id,
                    name=f"user_{user.id}",
                    age=None,
                    gender=None,
                    city=None,
                    bio="",
                    preferred_age_min=18,
                    preferred_age_max=99,
                    preferred_city=None,
                    preferred_gender=None,
                ),
            )
        return {
            "message": "User already exists",
            "user_id": user.id,
            "already_registered": True,
        }
    user = await create_user(db, body.telegram_id)
    await create_profile(
        db,
        ProfileCreate(
            user_id=user.id,
            name=f"user_{user.id}",
            age=None,
            gender=None,
            city=None,
            bio="",
            preferred_age_min=18,
            preferred_age_max=99,
            preferred_city=None,
            preferred_gender=None,
        ),
    )
    return {
        "message": "User created successfully",
        "user_id": user.id,
        "already_registered": False,
    }
