from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from ranking.schema import RankedProfileResponse, RankingResponse
from ranking.service import (
    get_next_profile_from_feed,
    get_user_ranking,
    recalculate_user_ranking,
    warmup_feed_cache,
)

router = APIRouter(prefix="/ranking", tags=["Ranking"])


@router.post("/recalculate/{user_id}", response_model=RankingResponse)
async def recalculate_ranking_endpoint(user_id: int, db: AsyncSession = Depends(get_db)):
    ranking_obj = await recalculate_user_ranking(db, user_id)
    if not ranking_obj:
        raise HTTPException(status_code=404, detail="Profile for user not found")
    return ranking_obj


@router.get("/{user_id}", response_model=RankingResponse)
async def get_ranking_endpoint(user_id: int, db: AsyncSession = Depends(get_db)):
    ranking_obj = await get_user_ranking(db, user_id)
    if not ranking_obj:
        raise HTTPException(status_code=404, detail="Profile for user not found")
    return ranking_obj


@router.post("/feed/start/{user_id}")
async def start_feed_endpoint(user_id: int, db: AsyncSession = Depends(get_db)):
    warmed = await warmup_feed_cache(db, user_id)
    if not warmed:
        raise HTTPException(status_code=404, detail="No candidate profiles available")
    first = await get_next_profile_from_feed(db, user_id)
    if not first:
        raise HTTPException(status_code=404, detail="No candidate profiles available")
    return first


@router.get("/feed/next/{user_id}", response_model=RankedProfileResponse)
async def next_feed_profile_endpoint(user_id: int, db: AsyncSession = Depends(get_db)):
    profile = await get_next_profile_from_feed(db, user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="No candidate profiles available")
    return profile
