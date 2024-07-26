from datetime import datetime, timezone
from src.enums import MessageType


def check_valid_time(
    time_to_check: str,
    min_send_time: int = MessageType.text.value.min_time,
    max_send_time: int = MessageType.text.value.max_time,
):
    datetime_to_check = datetime.fromisoformat(time_to_check)
    return (
        datetime_to_check.hour >= min_send_time
        and datetime_to_check.hour < max_send_time
    )


def is_online_recently(last_online_str: str, seconds: int = 5):
    last_online = datetime.fromisoformat(last_online_str)
    now = datetime.now(timezone.utc)
    difference = now - last_online
    return difference.total_seconds() <= seconds
