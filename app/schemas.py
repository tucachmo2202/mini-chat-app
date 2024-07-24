from pydantic import BaseModel
from typing import Optional


class UserCreate(BaseModel):
    username: str
    password: str
    email: str
    name: str


class MessageCreate(BaseModel):
    user_id: str
    text: str
    url: Optional[str]
