from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError

from database import get_db
from profiles.schema import (
    ProfileCreate,
    ProfilePhotoCreate,
    ProfilePhotoResponse,
    ProfileResponse,
    ProfileUpdate,
)
from profiles.service import (
    add_profile_photo,
    create_profile,
    delete_profile_photo,
    delete_profile,
    get_profile_by_id,
    get_profile_by_user_id,
    get_profile_photos,
    get_profiles,
    update_profile,
)
from ranking.service import recalculate_user_ranking

router = APIRouter(prefix="/profiles", tags=["Profiles"])


@router.post("/", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile_endpoint(body: ProfileCreate, db=Depends(get_db)):
    try:
        profile = await create_profile(db, body)
        await recalculate_user_ranking(db, profile.user_id)
        return profile
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Profile with this user_id or name already exists",
        ) from exc


@router.get("/", response_model=list[ProfileResponse])
async def list_profiles_endpoint(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    db=Depends(get_db),
):
    return await get_profiles(db, skip=skip, limit=limit)


@router.get("/by-user/{user_id}", response_model=ProfileResponse)
async def get_profile_by_user_endpoint(user_id: int, db=Depends(get_db)):
    profile = await get_profile_by_user_id(db, user_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return profile


@router.get("/{profile_id}", response_model=ProfileResponse)
async def get_profile_endpoint(profile_id: int, db=Depends(get_db)):
    profile = await get_profile_by_id(db, profile_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return profile


@router.put("/{profile_id}", response_model=ProfileResponse)
async def update_profile_endpoint(profile_id: int, body: ProfileUpdate, db=Depends(get_db)):
    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided for update",
        )
    try:
        updated = await update_profile(db, profile_id, update_data)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
            )
        await recalculate_user_ranking(db, updated.user_id)
        return updated
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Profile with this user_id or name already exists",
        ) from exc


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile_endpoint(profile_id: int, db=Depends(get_db)):
    deleted = await delete_profile(db, profile_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")


@router.post("/{profile_id}/photos", response_model=ProfilePhotoResponse, status_code=status.HTTP_201_CREATED)
async def add_profile_photo_endpoint(profile_id: int, body: ProfilePhotoCreate, db=Depends(get_db)):
    photo = await add_profile_photo(db, profile_id, body.telegram_file_id)
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    profile = await get_profile_by_id(db, profile_id)
    if profile:
        await recalculate_user_ranking(db, profile.user_id)
    return photo


@router.get("/{profile_id}/photos", response_model=list[ProfilePhotoResponse])
async def list_profile_photos_endpoint(profile_id: int, db=Depends(get_db)):
    profile = await get_profile_by_id(db, profile_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return await get_profile_photos(db, profile_id)


@router.post("/by-user/{user_id}/photos", response_model=ProfilePhotoResponse, status_code=status.HTTP_201_CREATED)
async def add_photo_by_user_endpoint(user_id: int, body: ProfilePhotoCreate, db=Depends(get_db)):
    profile = await get_profile_by_user_id(db, user_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    photo = await add_profile_photo(db, profile.id, body.telegram_file_id)
    await recalculate_user_ranking(db, user_id)
    return photo


@router.delete("/{profile_id}/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile_photo_endpoint(profile_id: int, photo_id: int, db=Depends(get_db)):
    deleted = await delete_profile_photo(db, profile_id, photo_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")
    profile = await get_profile_by_id(db, profile_id)
    if profile:
        await recalculate_user_ranking(db, profile.user_id)
