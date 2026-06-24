"""JWT token denylist backed by Redis.

Stores revoked ``jti`` values with a TTL matching the token's remaining
lifetime so entries self-expire exactly when the original token would.
See finding F-07 in the security review.
"""

from __future__ import annotations

from src.app.core.redis_client import RedisClient

_DENYLIST_PREFIX = "oauth:jwt:denylist:"


async def revoke(jti: str, ttl_seconds: int) -> None:
    """Mark ``jti`` as revoked for ``ttl_seconds``.

    No-ops if ``ttl_seconds <= 0`` (token already expired — nothing to revoke).
    """
    if ttl_seconds <= 0:
        return
    await RedisClient.set(f"{_DENYLIST_PREFIX}{jti}", "1", ttl=ttl_seconds)


async def is_revoked(jti: str) -> bool:
    """Return ``True`` if ``jti`` is on the denylist.

    An empty or ``None`` jti is treated as not-revoked (forward-compatible
    with tokens that predate F-07).
    """
    if not jti:
        return False
    value = await RedisClient.get(f"{_DENYLIST_PREFIX}{jti}")
    return value is not None
