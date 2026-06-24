"""JWT token denylist backed by Redis.

Stores revoked ``jti`` values with a TTL matching the token's remaining
lifetime so entries self-expire exactly when the original token would.
See finding F-07 in the security review.

Availability contract: ``is_revoked`` is fail-open — if Redis is unreachable
it logs a warning and returns ``False`` (best-effort denylist, bounded by
token TTL). ``revoke`` surfaces errors so callers know the revocation failed.
"""

from __future__ import annotations

import logging

from src.app.core.redis_client import RedisClient

logger = logging.getLogger(__name__)

_DENYLIST_PREFIX = "oauth:jwt:denylist:"


async def revoke(jti: str, ttl_seconds: int) -> None:
    """Mark ``jti`` as revoked for ``ttl_seconds``.

    No-ops if ``ttl_seconds <= 0`` (token already expired — nothing to revoke).
    Errors from Redis propagate so the caller can handle them.
    """
    if ttl_seconds <= 0:
        return
    await RedisClient.set(f"{_DENYLIST_PREFIX}{jti}", "1", ttl=ttl_seconds)


async def is_revoked(jti: str) -> bool:
    """Return ``True`` if ``jti`` is on the denylist.

    An empty or ``None`` jti is treated as not-revoked (forward-compatible
    with tokens that predate F-07).

    Fail-open: if Redis is unavailable, logs a warning and returns ``False``
    so that a Redis outage does not take down every authenticated endpoint.
    The window of exposure is bounded by the token's remaining TTL.
    """
    if not jti:
        return False
    try:
        value = await RedisClient.get(f"{_DENYLIST_PREFIX}{jti}")
    except Exception as exc:
        logger.warning(
            "token_denylist: Redis unavailable, failing open for jti check: %s", exc
        )
        return False
    return value is not None
