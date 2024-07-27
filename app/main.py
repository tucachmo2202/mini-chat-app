import json
from datetime import datetime, timezone
import asyncio
import uuid
from fastapi import (
    FastAPI,
    Depends,
    WebSocket,
    HTTPException,
    WebSocketDisconnect,
    status,
    WebSocketException,
)
from fastapi.security import OAuth2PasswordRequestForm
from redis import Redis
from broadcaster import Broadcast
from typing import Dict, List
from src.utils import check_valid_time, is_online_recently
from src.redis_utils import get_cache_client
from src.enums import MessageType, ResponseMessageType
from src.models import User, Message, UserCreate, ResponseMessage
from src.auth import hash_password, authenticate_user, get_current_user, verify_user
from src.constants import MAX_CLIENTS


# redis://user:password@url:port
websocket_list = []
message_queue = asyncio.Queue(maxsize=500)
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
        created_at=datetime.now(timezone.utc).isoformat(),
        last_online=datetime.now(timezone.utc).isoformat(),
    )
    if redis.exists(f"user:{user.username}"):
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE, detail="username already in use"
        )
    else:
        redis.hmset(f"user:{user.username}", user_data.model_dump())
    return {"msg": "User registered successfully"}


@app.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    redis: Redis = Depends(get_cache_client),
):
    token = authenticate_user(redis, form_data.username, form_data.password)
    if token is None:
        raise HTTPException(
            status_code=400,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"access_token": token, "token_type": "bearer"}


@app.websocket("/ws/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: str,
    token: str,
    redis: Redis = Depends(get_cache_client),
):
    if len(websocket_list) >= MAX_CLIENTS:
        raise WebSocketException(
            code=status.WS_1013_TRY_AGAIN_LATER, reason="Too many websockets"
        )
    await websocket.accept()
    websocket_list.append(websocket)
    user_infor: User = await get_current_user(token)
    if user_infor is None or user_infor.username != room_id:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="user not found",
        )
        websocket_list.remove(websocket)
        return {"username": user_infor, "room_id": room_id}
    async with broadcast.subscribe(channel=f"chat_{room_id}") as subscriber:
        try:
            while True:
                data = await websocket.receive_text()
                redis.hset(
                    name=f"user:{user_infor.username}",
                    key="last_online",
                    value=datetime.now(timezone.utc).isoformat(),
                )
                message_infor = json.loads(data)
                type_message = message_infor["type"]
                send_time = message_infor["send_time"]
                if type_message == "text":
                    additional_message_infor = MessageType.text.value
                elif type_message == "voice":
                    additional_message_infor = MessageType.voice.value
                elif type_message == "video":
                    additional_message_infor = MessageType.video.value
                else:
                    error_message = ResponseMessage(
                        type=ResponseMessageType.error,
                        message=f"You send messages type {type_message} is invalid",
                    )
                    await broadcast.publish(
                        channel=f"chat_{room_id}",
                        message=json.dumps(error_message.model_dump()),
                    )
                    event = await subscriber.get()
                    await websocket.send_text(event.message)
                    continue
                if not check_valid_time(
                    send_time,
                    additional_message_infor.min_time,
                    additional_message_infor.max_time,
                ):
                    error_message = ResponseMessage(
                        type=ResponseMessageType.error,
                        message=f"You can't send {type_message} messages in this time",
                    )
                    await broadcast.publish(
                        channel=f"chat_{room_id}",
                        message=json.dumps(error_message.model_dump()),
                    )
                    event = await subscriber.get()
                    await websocket.send_text(event.message)
                    continue

                message = Message(
                    id=str(uuid.uuid4()),
                    room_id=room_id,
                    text=message_infor["text"],
                    type=additional_message_infor.type,
                    send_time=message_infor["send_time"],
                )

                # check client alive to close the connection
                user_data = User(**redis.hgetall(f"user:{user_infor.username}"))
                if not is_online_recently(user_data.last_online):
                    await websocket.close(reason="client disconnect")
                    websocket_list.remove(websocket)
                    return {}

                reply_message = ResponseMessage(
                    type=ResponseMessageType.reply,
                    message="Thanks for send me a message",
                )

                time_utc = datetime.fromisoformat(
                    message_infor["send_time"]
                ).astimezone(timezone.utc)

                redis.zadd(
                    f"messages:{room_id}",
                    {json.dumps(message.model_dump()): time_utc.timestamp()},
                )
                await broadcast.publish(
                    channel=f"chat_{room_id}",
                    message=json.dumps(reply_message.model_dump()),
                )
                event = await subscriber.get()
                await websocket.send_text(event.message)
        except WebSocketDisconnect:
            websocket_list.remove(websocket)


@app.post("/heartbeat", response_model=Dict)
async def update_heartbeat(
    user_infor: User = Depends(verify_user), redis: Redis = Depends(get_cache_client)
):
    if user_infor is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not allow to call heartbeat",
        )

    redis.hset(
        name=f"user:{user_infor.username}",
        key="last_online",
        value=datetime.now(timezone.utc).isoformat(),
    )
    return {}


@app.get("/messages/{room_id}", response_model=List[Message])
async def get_messages(
    room_id: str,
    time_start: str = None,
    time_end: str = None,
    page: int = 0,
    page_size: int = 10,
    user_infor: User = Depends(verify_user),
    redis: Redis = Depends(get_cache_client),
):
    if user_infor is None or user_infor.username != room_id:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail="Not allow to read message to this room",
        )
    if time_start is not None:
        try:
            time_start = (
                datetime.fromisoformat(time_start).astimezone(timezone.utc).timestamp()
            )
        except:  # noqa: E722
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="time_start not a valid datetime with iso format",
            )
    else:
        time_start = "-inf"
    if time_end is not None:
        try:
            time_end = (
                datetime.fromisoformat(time_end).astimezone(timezone.utc).timestamp()
            )
        except:  # noqa: E722
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="time_end not a valid datetime with iso format",
            )
    else:
        time_end = "inf"
    start_index = page * page_size
    # end_index = start_index + page_size - 1
    messages = redis.zrangebyscore(
        f"messages:{room_id}",
        min=time_start,
        max=time_end,
        start=start_index,
        num=page_size,
    )
    return [Message(**json.loads(msg)) for msg in messages]
