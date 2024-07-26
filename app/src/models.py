from pydantic import BaseModel
from typing import Optional


class UserCreate(BaseModel):
    username: str
    password: str
    email: str
    name: str


class User(UserCreate):
    id: str
    last_online: str
    created_at: str


class Message(BaseModel):
    id: str
    room_id: str
    type: int = 0
    text: Optional[str] = None
    url: Optional[str] = None
    send_time: str


class ResponseMessage(BaseModel):
    type: str
    message: str
