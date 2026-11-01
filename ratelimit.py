"""Small in-memory sliding-window rate limiter (per user, per process). Protects paid API calls."""
import os
import threading
import time
from collections import defaultdict, deque

_lock = threading.Lock()
_events = defaultdict(deque)


def limit_per_hour() -> int:
    try:
        return max(1, int(os.getenv("AI_REPLIES_PER_HOUR", "40")))
    except ValueError:
        return 40


def allow(user_id, bucket: str, limit: int | None = None, window: float = 3600.0) -> bool:
    """Record an attempt and return True if the user is still within the limit."""
    limit = limit or limit_per_hour()
    now = time.time()
    with _lock:
        q = _events[(user_id, bucket)]
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= limit:
            return False
        q.append(now)
        return True


def reset():
    with _lock:
        _events.clear()
