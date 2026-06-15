"""Feature flags service backed by Redis.

Flags are read from Redis first; if absent, the value falls back to
environment-driven settings (``Settings``) and finally to the default.
"""

from __future__ import annotations

from logging import getLogger

from src.app.core.config import settings
from src.app.core.redis_client import RedisClient

logger = getLogger(__name__)


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
