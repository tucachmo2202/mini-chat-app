import json
from datetime import datetime, timezone
from fastapi import (
    FastAPI,
    Depends,
    WebSocket,
    HTTPException,
    WebSocketDisconnect,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm
import uuid
from redis import Redis
from broadcaster import Broadcast
from redis_utils import get_cache_client
from models import User, Message
from schemas import UserCreate, MessageCreate
from auth import hash_password, authenticate_user, get_current_user


# redis://user:password@url:port
broadcast = Broadcast("redis://:password@redis:6379")
app = FastAPI(on_startup=[broadcast.connect], on_shutdown=[broadcast.disconnect])


@app.post("/register")
async def register(user: UserCreate, redis: Redis = Depends(get_cache_client)):
    user_id = str(uuid.uuid4())
    user_data = User(
        id=user_id,
        username=user.username,
        password=hash_password(user.password),
        email=user.email,
        name=user.name,
    )
    redis.hmset(f"user:{user.username}", user_data.model_dump())
    return {"msg": "User registered successfully"}


@app.post("/token")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    redis: Redis = Depends(get_cache_client),
):
    user = authenticate_user(redis, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=400,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"access_token": form_data.username, "token_type": "bearer"}


@app.websocket("/ws/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: str,
    token: str = Depends(get_current_user),
    redis: Redis = Depends(get_cache_client),
):
    if token != room_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not allow to send message to this room",
        )
    await websocket.accept()
    async with broadcast.subscribe(channel=f"chat_{room_id}") as subscriber:
        try:
            while True:
                data = await websocket.receive_text()
                message = Message(
                    room_id=room_id,
                    text=data,
                    send_time=datetime.now(timezone.utc).isoformat(),
                )
                redis.zadd(
                    f"messages:{room_id}",
                    {json.dumps(message.model_dump()): message.send_time.timestamp()},
                )
                await broadcast.publish(
                    channel=f"chat_{room_id}", message=json.dumps(message.model_dump())
                )
                event = await subscriber.get()
                await websocket.send_text(event.message)
        except WebSocketDisconnect:
            pass


# @app.post("/messages")
# async def send_message(
#     message: MessageCreate,
#     user: dict = Depends(get_current_user),
#     redis: Redis = Depends(get_cache_client),
# ):
#     message_id = str(uuid.uuid4())
#     send_time = datetime.now(timezone.utc).timestamp()
#     message_data = Message(
#         id=message_id,
#         room_id=message.room_id,
#         text=message.text,
#         url=message.url,
#         send_time=send_time,
#     )
#     redis.zadd(
#         f"messages:{message.room_id}",
#         {json.dumps(message_data.model_dump()): send_time},
#     )
#     await broadcast.publish(
#         channel=message.room_id, message=json.dumps(message_data.model_dump())
#     )
#     return {"msg": "Message sent"}


@app.get("/messages/{room_id}")
async def get_messages(
    room_id: str,
    page: int = 0,
    page_size: int = 10,
    redis: Redis = Depends(get_cache_client),
):
    start_index = page * page_size
    end_index = start_index + page_size - 1
    messages = redis.zrange(f"messages:{room_id}", start_index, end_index)
    return [json.loads(msg) for msg in messages]
