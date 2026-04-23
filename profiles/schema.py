from typing import Optional

from pydantic import BaseModel


class ProfileCreate(BaseModel):
    user_id: int
    name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    city: Optional[str] = None
    bio: Optional[str] = None
    preferred_age_min: int
    preferred_age_max: int
    preferred_city: Optional[str] = None
    preferred_gender: Optional[str] = None


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    city: Optional[str] = None
    bio: Optional[str] = None
    preferred_age_min: Optional[int] = None
    preferred_age_max: Optional[int] = None
    preferred_city: Optional[str] = None
    preferred_gender: Optional[str] = None


class ProfileResponse(BaseModel):
    id: int
    user_id: int
    name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    city: Optional[str] = None
    bio: Optional[str] = None
    photos_count: int
    preferred_age_min: int
    preferred_age_max: int
    preferred_city: Optional[str] = None
    preferred_gender: Optional[str] = None

    class Config:
        from_attributes = True


class ProfilePhotoCreate(BaseModel):
    telegram_file_id: str


class ProfilePhotoResponse(BaseModel):
    id: int
    profile_id: int
    telegram_file_id: str

    class Config:
        from_attributes = True