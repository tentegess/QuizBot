from bson.objectid import ObjectId
from pydantic import BaseModel
from typing import List, Optional
from model.option_model import OptionModel

class QuestionModel(BaseModel):
    question: str
    options: List[OptionModel]
    image_url: Optional[ObjectId]

    class Config:
        arbitrary_types_allowed = True