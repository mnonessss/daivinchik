from pydantic import BaseModel, ConfigDict


class RankingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    primary_score: float
    behavioral_score: float
    final_score: float


class RankedProfileResponse(BaseModel):
    profile_id: int
    user_id: int
    name: str
    age: int | None
    gender: str | None
    city: str | None
    bio: str | None
    final_score: float
