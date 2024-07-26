from enum import Enum
from dataclasses import dataclass


@dataclass
class MessageInfo:
    type: int
    min_time: int
    max_time: int


class MessageType(Enum):
    text = MessageInfo(type=0, min_time=5, max_time=24)
    voice = MessageInfo(type=0, min_time=8, max_time=24)
    video = MessageInfo(type=0, min_time=20, max_time=24)


class ResponseMessageType(Enum):
    notification = "notification"
    error = "error"
    reply = "reply"
