from pydantic import BaseModel
from typing import Optional


class User(BaseModel):
    id: str
    username: str
    password: str
    email: str
    name: str


class Message(BaseModel):
    id: str
    user_id: str
    text: Optional[str] = None
    url: Optional[str] = None
    send_time: str
