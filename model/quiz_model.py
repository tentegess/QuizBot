from datetime import datetime
from bson import ObjectId
from pydantic import BaseModel
from typing import List


class QuizModel(BaseModel):
    title: str
    created_at: datetime
    updated_at: datetime
    questions: List[ObjectId]