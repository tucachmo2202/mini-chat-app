import os
import redis


def get_cache_client():
    host = os.getenv("REDIS_HOST", "redis")
    port = os.getenv("REDIS_PORT", "6379")
    client = redis.Redis(
        host=host, port=port, decode_responses=True, password="password"
    )
    return client


def save_user(username: str, password: str, redis_client: redis.Redis):
    redis_client.hset("users", username, password)


def get_user_password(username: str, redis_client: redis.Redis):
    return redis_client.hget("users", username)
