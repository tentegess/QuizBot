from pydantic import BaseModel, Field
from bson import ObjectId
from datetime import datetime
from typing import List, Optional
from model.PyId import PyObjectId

class ResultModel(BaseModel):
    id: Optional[PyObjectId] = Field(None, alias="_id")
    game_id: PyObjectId
    guild_id: int
    user_id: int
    score: int
    finished_at: datetime

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}