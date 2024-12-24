from pydantic import BaseModel
from bson import ObjectId
from datetime import datetime
from typing import List, Optional

class GameModel(BaseModel):
    quiz_id: ObjectId
    players: List[int]
    current_question_index: int
    started_at: datetime
    finished_at: Optional[datetime]
