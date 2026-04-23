from pydantic import BaseModel


class RankingResponse(BaseModel):
    user_id: int
    primary_score: float
    behavioral_score: float
    final_score: float

    class Config:
        from_attributes = True


class RankedProfileResponse(BaseModel):
    profile_id: int
    user_id: int
    name: str
    age: int | None
    gender: str | None
    city: str | None
    bio: str | None
    final_score: float
