from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


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
    model_config = ConfigDict(from_attributes=True)

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


class ProfilePhotoCreate(BaseModel):
    telegram_file_id: str


class ProfilePhotoResponse(BaseModel):
    id: int
    profile_id: int
    telegram_file_id: str | None = None
    s3_object_key: str | None = None
    url: str | None = Field(default=None, description="Presigned GET URL when photo is stored in S3")