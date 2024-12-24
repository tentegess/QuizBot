from bson import ObjectId
from pydantic import BaseModel
from typing import List, Optional

class QuestionModel(BaseModel):
    text: str
    options: List[str]
    correct_answer_index: int
    image_url: Optional[ObjectId]
