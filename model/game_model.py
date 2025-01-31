from pydantic import BaseModel, Field
from bson import ObjectId
from datetime import datetime
from typing import List, Optional
from model.PyId import PyObjectId

class GameModel(BaseModel):
    id: Optional[PyObjectId] = Field(None, alias="_id")
    guild_id: int
    quiz_code: str
    finished_at: datetime

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
