from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from interactions.schema import InteractionCreate, InteractionResponse
from interactions.service import create_interaction

router = APIRouter(prefix="/interactions", tags=["Interactions"])


@router.post("/", response_model=InteractionResponse, status_code=status.HTTP_201_CREATED)
async def create_interaction_endpoint(
    body: InteractionCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await create_interaction(db, body.from_user, body.to_user, body.action)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
