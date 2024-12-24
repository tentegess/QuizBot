from bson import ObjectId
from pydantic import BaseModel


class AnswerModel(BaseModel):
    user_id: int
    question_id: ObjectId
    game_id: ObjectId
    selected_option_index: int
