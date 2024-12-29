from datetime import datetime
from pydantic import BaseModel
from typing import List
from model.question_model import QuestionModel


class QuizModel(BaseModel):
    title: str
    created_at: datetime
    updated_at: datetime
    user_id: int
    questions: List[QuestionModel]
    access_code: str = None

    class Config:
        arbitrary_types_allowed = True
