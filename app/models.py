from pydantic import BaseModel
from typing import Optional


class UserCreate(BaseModel):
    username: str
    password: str
    email: str
    name: str


class User(UserCreate):
    created_at: str


class Message(BaseModel):
    id: str
    user_id: str
    text: Optional[str] = None
    url: Optional[str] = None
    send_time: str
