from re import S
from typing import Optional
from pydantic import BaseModel

class ProfileCreate(BaseModel):
    name: str
    age: int
    gender: str
    city: str
    bio: str
    preferred_age_min: int
    preferred_age_max: int
    preferred_city: str
    preferred_gender: str


class ProfileUpdate(BaseModel):
    name: str
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
    name: str
    age: int
    gender: str
    city: str
    bio: str
    preferred_age_min: int
    preferred_age_max: int
    preferred_city: str
    preferred_gender: str

    class Config:
        from_attributes = True