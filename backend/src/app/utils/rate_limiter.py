import os

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)


def conditional_limit(rate: str):
    """Apply rate limit only in production."""
    def decorator(func):
        if os.getenv("ENVIRONMENT") == "production" and not os.getenv("CI"):
            return limiter.limit(rate)(func)
        return func
    return decorator