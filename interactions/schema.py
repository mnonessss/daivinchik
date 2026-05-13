from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

InteractionAction = Literal["like", "skip", "dialog_start"]


class InteractionCreate(BaseModel):
    from_user: int
    to_user: int
    action: InteractionAction


class InteractionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    from_user: int
    to_user: int
    action: str
    created_at: datetime
