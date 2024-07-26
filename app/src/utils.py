from datetime import datetime
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
