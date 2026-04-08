from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from functools import wraps

from flask import jsonify, request


_lock = threading.Lock()
_hits = defaultdict(deque)


def rate_limit(max_requests: int, window_seconds: int):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            client_id = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()
            path = request.path
            key = f"{client_id}:{path}"
            now = time.time()

            with _lock:
                dq = _hits[key]
                while dq and (now - dq[0]) > window_seconds:
                    dq.popleft()
                if len(dq) >= max_requests:
                    retry_after = max(1, int(window_seconds - (now - dq[0])))
                    return (
                        jsonify(
                            {
                                "error": "Rate limit exceeded. Slow down emergency submissions.",
                                "retry_after_seconds": retry_after,
                            }
                        ),
                        429,
                    )
                dq.append(now)

            return fn(*args, **kwargs)

        return wrapper

    return decorator
