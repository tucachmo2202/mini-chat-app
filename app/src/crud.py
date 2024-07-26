import redis
import json
from src.models import User, Message

r = redis.Redis(host="redis", port=6379, db=0)


def save_user(user: User):
    r.set(f"user:{user.username}", json.dumps(user.model_dump()))


def get_user_by_username(username: str):
    user_data = r.get(f"user:{username}")
    if user_data:
        return User(**json.loads(user_data))
    return None


def save_message(message: Message):
    message_data = message.model_dump()
    r.zadd(f"messages:{message.user_id}", {json.dumps(message_data): message.send_time})


def get_messages(room_id: str, start_time: str, page_size: int):
    # start_index = page * page_size
    # end_index = start_index + page_size - 1
    messages = r.zrangebyscore(f"messages:{room_id}", min=start_time, num=page_size)
    return [json.loads(msg) for msg in messages]
