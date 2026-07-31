"""Feature flags service backed by Redis.

Flags are read from Redis first; if absent, the value falls back to
environment-driven settings (``Settings``) and finally to the default.
"""

from __future__ import annotations

from logging import getLogger

from src.app.core.config import settings
from src.app.core.redis_client import RedisClient

logger = getLogger(__name__)

# Зарегистрированные фичатоглы проекта.
# Добавляй сюда новые тоглы, чтобы они появлялись в админке.
KNOWN_FEATURE_FLAGS = ["google_oauth", "catalog_search_meilisearch"]


async def is_enabled(flag: str, default: bool = False) -> bool:
    """Return whether ``flag`` is enabled.

    Priority:
        1. Redis value (feature:<flag>)
        2. ``settings.<flag>_enabled`` if it exists
        3. ``default``

    Redis errors are treated as a miss, so the request keeps working even
    if Redis is temporarily unavailable.
    """
    try:
        redis_value = await RedisClient.get(f"feature:{flag}")
        if redis_value is not None:
            return redis_value == "1"
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.warning("Failed to read feature flag %s from Redis: %s", flag, exc)

    env_attr = f"{flag}_enabled"
    env_value = getattr(settings, env_attr, None)
    if isinstance(env_value, bool):
        return env_value

    return default


async def set_enabled(flag: str, enabled: bool) -> None:
    """Persist a feature flag value in Redis."""
    await RedisClient.set(f"feature:{flag}", "1" if enabled else "0", ttl=0)


async def get_redis_value(flag: str) -> bool | None:
    """Return Redis override for a flag, or None if not set."""
    try:
        redis_value = await RedisClient.get(f"feature:{flag}")
        if redis_value is not None:
            return redis_value == "1"
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed to read feature flag %s from Redis: %s", flag, exc)
    return None


def get_env_default(flag: str) -> bool | None:
    """Return env-driven default for a flag if it exists."""
    env_attr = f"{flag}_enabled"
    env_value = getattr(settings, env_attr, None)
    return env_value if isinstance(env_value, bool) else None


async def get_flag_status(flag: str, default: bool = False) -> dict:
    """Return full status of a feature flag: env default, Redis override, effective value."""
    env_default = get_env_default(flag)
    redis_override = await get_redis_value(flag)
    effective = redis_override if redis_override is not None else (env_default if env_default is not None else default)

    source = "redis"
    if redis_override is None:
        source = "env" if env_default is not None else "default"

    return {
        "name": flag,
        "enabled": effective,
        "env_default": env_default,
        "redis_override": redis_override,
        "source": source,
    }


async def list_flags(default: bool = False) -> list[dict]:
    """Return status for all known feature flags."""
    return [await get_flag_status(flag, default=default) for flag in KNOWN_FEATURE_FLAGS]
