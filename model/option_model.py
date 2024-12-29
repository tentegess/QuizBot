from pydantic import BaseModel


class OptionModel(BaseModel):
    option: str
    is_correct: bool
