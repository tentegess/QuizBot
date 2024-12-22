from datetime import datetime
from pydantic import BaseModel


class SessionModel(BaseModel):
    token: str
    refresh_token: str
    token_expires_at: datetime
    user_id: int