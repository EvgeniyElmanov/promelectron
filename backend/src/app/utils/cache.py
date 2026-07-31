import functools
import inspect
import json

from fastapi import Request
from fastapi.encoders import jsonable_encoder

from src.app.core.redis_client import redis_client


def build_cache_key(request: Request) -> str:
    path = request.url.path
    query = str(request.query_params)
    if query:
        sorted_query = "&".join(sorted(query.split("&")))
        return f"{path}?{sorted_query}"
    return path


def cache_response(ttl_seconds: int):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            request: Request | None = kwargs.pop("request", None)
            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if request is None:
                return await func(*args, **kwargs)

            cache_key = build_cache_key(request)

            try:
                cached = await redis_client.get(cache_key)
                if cached is not None:
                    return json.loads(cached)
            except Exception:
                pass  # Redis error, fall through to handler

            response = await func(*args, **kwargs)

            try:
                serialized = json.dumps(jsonable_encoder(response))
                await redis_client.set(cache_key, serialized, ttl_seconds)
            except Exception:
                pass  # Redis error, don't fail the request

            return response

        sig = inspect.signature(func)
        params = list(sig.parameters.values())
        if not any(p.name == "request" for p in params):
            params.append(
                inspect.Parameter(
                    "request",
                    inspect.Parameter.KEYWORD_ONLY,
                    default=None,
                    annotation=Request,
                )
            )
            wrapper.__signature__ = sig.replace(parameters=params)

        return wrapper

    return decorator


async def invalidate_cache(pattern: str) -> None:
    try:
        await redis_client.delete_pattern(pattern)
    except Exception:
        pass
