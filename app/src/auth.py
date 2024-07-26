from typing import Union, Any, Dict
import jwt
import hashlib
from fastapi import HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from redis import Redis
from src.redis_utils import get_cache_client
from src.constants import DEFAULT_SECRET_KEY, DEFAULT_ALGORITHM
from src.models import User


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
# redis = Redis(host="redis://redis", port=6379, db=0)


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def authenticate_user(redis: Redis, username: str, password: str):
    user_data = redis.hgetall(f"user:{username}")
    print("user_data", user_data)
    if not user_data or user_data.get("password") != hash_password(password):
        return None
    else:
        user_infor = {
            "id": user_data["id"],
            "username": user_data["username"],
            "email": user_data["email"],
            "name": user_data["name"],
        }
        token = encode_token(subject=user_infor)
        return token


async def verify_user(request: Request):
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
    return user_infor


def encode_token(
    subject: Union[str, Any],
    secret_key: str = DEFAULT_SECRET_KEY,
    algorithm: str = DEFAULT_ALGORITHM,
) -> str:
    payload = subject
    encode_token_jwt = jwt.encode(payload, key=secret_key, algorithm=algorithm)
    return encode_token_jwt


def decode_token(
    encode_token: str,
    secret_key: str = DEFAULT_SECRET_KEY,
    algorithms: str = DEFAULT_ALGORITHM,
) -> Dict:
    try:
        decode_token = jwt.decode(encode_token, key=secret_key, algorithms=algorithms)
    except jwt.exceptions.DecodeError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )
    return decode_token


async def get_current_user(token: str):
    user_infor = decode_token(token)
    redis = get_cache_client()
    if "username" not in user_infor:
        return None
    user_data = redis.hgetall(f"user:{user_infor['username']}")
    if not user_data:
        return None
    return User(**user_data)
