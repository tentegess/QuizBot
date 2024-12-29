from pydantic import BaseModel
from bson import ObjectId
from datetime import datetime
from typing import List

class GameModel(BaseModel):
    quiz_id: ObjectId
    players: List[int]
    started_at: datetime
