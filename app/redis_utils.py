import os
import redis


# redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)


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


def save_message(channel: str, username: str, message: str, redis_client: redis.Redis):
    redis_client.rpush(f"messages:{channel}", f"{username}: {message}")


def get_messages(channel: str, redis_client: redis.Redis):
    return redis_client.lrange(f"messages:{channel}", 0, -1)


def save_channel(channel: str, user1: str, user2: str, redis_client: redis.Redis):
    redis_client.hset("channels", channel, f"{user1},{user2}")


def get_channel_users(channel: str, redis_client: redis.Redis):
    users = redis_client.hget("channels", channel)
    return users.split(",") if users else None
