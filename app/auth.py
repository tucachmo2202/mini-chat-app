import hashlib
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from redis import Redis

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
redis = Redis(host="redis://redis", port=6379, db=0)


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def authenticate_user(username: str, password: str):
    user_data = redis.hgetall(f"user:{username}")
    if not user_data or user_data.get("password") != hash_password(password):
        return False
    return user_data


async def get_current_user(token: str = Depends(oauth2_scheme)):
    user_data = redis.hgetall(f"user:{token}")
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_data
