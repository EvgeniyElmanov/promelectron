import os

from slowapi import Limiter
from slowapi.util import get_remote_address

from src.app.core.config import settings


_redis_url = settings.redis_url if settings.redis_url else "memory://"

if os.getenv("ENVIRONMENT") == "production" and not os.getenv("CI"):
    # Distributed rate limiting backed by Redis in production.
    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri=_redis_url,
        storage_options={"socket_connect_timeout": "5"},
    )
else:
    # In-memory storage for dev/test/CI.
    limiter = Limiter(key_func=get_remote_address)


def conditional_limit(rate: str):
    """Apply rate limit only in production."""
    def decorator(func):
        if os.getenv("ENVIRONMENT") == "production" and not os.getenv("CI"):
            return limiter.limit(rate)(func)
        return func
    return decorator
