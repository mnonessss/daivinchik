from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from database import get_db
from profiles.schema import ProfileCreate
from profiles.service import create_profile, get_profile_by_user_id
from referral import build_referral_code
from users.service import (
        create_user,
        get_user_by_id,
        get_user_by_telegram_id,
        update_user_last_active
    )

router = APIRouter(prefix="/users", tags=["Users"])


class RegisterBody(BaseModel):
    telegram_id: int
    referral_id: int | None = None


class UserResponse(BaseModel):
    id: int
    telegram_id: int
    referral_id: int | None = None


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
    referral_id = body.referral_id
    if referral_id is not None and referral_id <= 0:
        referral_id = None
    if referral_id is not None:
        referrer = await get_user_by_id(db, referral_id)
        if not referrer:
            referral_id = None
    user = await create_user(db, body.telegram_id, referral_id=referral_id)
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


@router.get("/referral/{user_id}")
async def get_referral_code(user_id: int):
    return {"referral_code": build_referral_code(user_id)}


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_endpoint(user_id: int, db=Depends(get_db)):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user
