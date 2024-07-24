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
from fastapi.concurrency import run_until_first_complete
from redis_utils import get_cache_client
from models import User, Message, UserCreate
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
        created_at=datetime.now(timezone.utc).isoformat(),
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
    await websocket.accept()
    # user_infor: User = await get_current_user(token)
    # if user_infor.username != room_id:
    #     raise HTTPException(
    #         status_code=status.HTTP_404_NOT_FOUND,
    #         detail="Not allow to send message to this room",
    #     )
    print("accepted")
    async with broadcast.subscribe(channel=f"chat_{room_id}") as subscriber:
        print("bat dau broadcaster  ")
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
                    {
                        json.dumps(message.model_dump()): datetime.fromisoformat(
                            message.send_time
                        ).timestamp()
                    },
                )
                print("add xong message")
                await broadcast.publish(
                    channel=f"chat_{room_id}", message=json.dumps(message.model_dump())
                )
                event = await subscriber.get()
                await websocket.send_text(event.message)
        except WebSocketDisconnect:
            pass


@app.get("/messages/{room_id}")
async def get_messages(
    room_id: str,
    page: int = 0,
    page_size: int = 10,
    user_infor: User = Depends(get_current_user),
    redis: Redis = Depends(get_cache_client),
):
    if not user_infor.username != room_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not allow to read message to this room",
        )
    start_index = page * page_size
    end_index = start_index + page_size - 1
    messages = redis.zrange(f"messages:{room_id}", start_index, end_index)
    return [json.loads(msg) for msg in messages]
