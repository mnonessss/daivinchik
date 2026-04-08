from fastapi import APIRouter, Depends
from pydantic import BaseModel

from database import get_db
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
        return {
            "message": "User already exists",
            "user_id": user.id,
            "already_registered": True,
        }
    user = await create_user(db, body.telegram_id)
    return {
        "message": "User created successfully",
        "user_id": user.id,
        "already_registered": False,
    }
