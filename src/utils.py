import os
from datetime import datetime, timezone, timedelta


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def days_ago_ms(days: int) -> int:
    dt = datetime.now(timezone.utc) - timedelta(days=days)
    return int(dt.timestamp() * 1000)


def now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def floor_hour_ms(ts_ms: int) -> int:
    dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
    floored = dt.replace(minute=0, second=0, microsecond=0)
    return int(floored.timestamp() * 1000) 