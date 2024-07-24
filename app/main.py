import json
from datetime import datetime, timezone
from fastapi import (
    FastAPI,
    Depends,
    WebSocket,
    HTTPException,
    WebSocketDisconnect,
    status,
    Request,
)
from fastapi.security import OAuth2PasswordRequestForm
import uuid
from redis import Redis
from broadcaster import Broadcast
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
    user_infor: User = await get_current_user(token)
    if user_infor is None or user_infor.username != room_id:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="user not found",
        )
        return {"username": user_infor, "room_id": room_id}
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
                    {
                        json.dumps(message.model_dump()): datetime.fromisoformat(
                            message.send_time
                        ).timestamp()
                    },
                )
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
    request: Request,
    page: int = 0,
    page_size: int = 10,
    redis: Redis = Depends(get_cache_client),
):
    token = request.headers.get("Authorization")
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is required"
        )
    if "Bearer" not in token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token type is not valid"
        )
    access_token = token.split(" ")[-1]
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is required.",
        )
    user_infor: User = await get_current_user(access_token)
    if user_infor is None or user_infor.username != room_id:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail="Not allow to read message to this room",
        )
    start_index = page * page_size
    end_index = start_index + page_size - 1
    messages = redis.zrange(f"messages:{room_id}", start_index, end_index, desc=True)
    return [json.loads(msg) for msg in messages]
