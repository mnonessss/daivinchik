from profiles.schema import ProfileCreate
from models import Profiles


async def create_profile(db, profile: ProfileCreate):
    profile = Profiles(
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
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


