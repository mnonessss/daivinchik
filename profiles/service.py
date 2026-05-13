import asyncio

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from models import ProfilePhotos, Profiles
from profiles.schema import ProfileCreate
from storage.s3_storage import delete_object_key, is_s3_enabled, upload_profile_photo as s3_put_object
from storage.telegram_download import download_telegram_photo


async def create_profile(db, profile: ProfileCreate):
    db_profile = Profiles(
        user_id=profile.user_id,
        name=profile.name,
        age=profile.age,
        gender=profile.gender,
        city=profile.city,
        bio=profile.bio,
        preferred_age_min=profile.preferred_age_min,
        preferred_age_max=profile.preferred_age_max,
        preferred_city=profile.preferred_city,
        preferred_gender=profile.preferred_gender,
    )
    db.add(db_profile)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise
    await db.refresh(db_profile)
    return db_profile


async def get_profile_by_id(db, profile_id: int):
    return await db.get(Profiles, profile_id)


async def get_profile_by_user_id(db, user_id: int):
    row = await db.execute(select(Profiles).where(Profiles.user_id == user_id))
    return row.scalar_one_or_none()


async def get_profiles(db, skip: int = 0, limit: int = 100):
    row = await db.execute(select(Profiles).offset(skip).limit(limit))
    return row.scalars().all()


async def update_profile(db, profile_id: int, update_data: dict):
    profile = await db.get(Profiles, profile_id)
    if not profile:
        return None
    for field, value in update_data.items():
        setattr(profile, field, value)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise
    await db.refresh(profile)
    return profile


async def delete_profile(db, profile_id: int):
    profile = await db.get(Profiles, profile_id)
    if not profile:
        return False
    await db.delete(profile)
    await db.commit()
    return True


async def add_profile_photo(db, profile_id: int, telegram_file_id: str):
    profile = await db.get(Profiles, profile_id)
    if not profile:
        return None

    s3_key = None
    if is_s3_enabled():
        body, content_type, ext = await download_telegram_photo(telegram_file_id)
        loop = asyncio.get_running_loop()
        s3_key = await loop.run_in_executor(
            None,
            lambda: s3_put_object(profile_id, body, content_type, ext),
        )

    photo = ProfilePhotos(
        profile_id=profile_id,
        telegram_file_id=telegram_file_id,
        s3_object_key=s3_key,
    )
    db.add(photo)
    profile.photos_count += 1
    await db.commit()
    await db.refresh(photo)
    return photo


async def get_profile_photos(db, profile_id: int):
    row = await db.execute(
        select(ProfilePhotos)
        .where(ProfilePhotos.profile_id == profile_id)
        .order_by(ProfilePhotos.created_at.desc())
    )
    return row.scalars().all()


async def delete_profile_photo(db, profile_id: int, photo_id: int):
    profile = await db.get(Profiles, profile_id)
    if not profile:
        return False

    photo = await db.get(ProfilePhotos, photo_id)
    if not photo or photo.profile_id != profile_id:
        return False

    if photo.s3_object_key and is_s3_enabled():
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, delete_object_key, photo.s3_object_key)

    await db.delete(photo)
    profile.photos_count = max((profile.photos_count or 0) - 1, 0)
    await db.commit()
    return True
