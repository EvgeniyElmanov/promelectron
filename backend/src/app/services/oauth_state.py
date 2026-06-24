"""OAuth state + PKCE helpers backed by Redis.

The OAuth ``state`` parameter is a cryptographically random, single-use
value that protects against CSRF / login-CSRF (issue #4 security review,
finding F-01). Alongside it we store a PKCE ``code_verifier`` (F-06) and
the originating provider, so the callback can resolve the provider from
``state`` (Q-1 decision) instead of trusting a client-supplied value.

State entries are short-lived (``STATE_TTL``) and deleted on first use.
"""

from __future__ import annotations

import base64
import hashlib
import json
import secrets

from src.app.core.redis_client import RedisClient

_STATE_PREFIX = "oauth:state:"
STATE_TTL = 600  # seconds — the user has 10 minutes to finish the login


def generate_pkce_pair() -> tuple[str, str]:
    """Return a ``(code_verifier, code_challenge)`` pair (PKCE, S256)."""
    code_verifier = secrets.token_urlsafe(64)  # 43..128 chars per RFC 7636
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return code_verifier, code_challenge


async def create_state(provider: str, code_verifier: str) -> str:
    """Create a random state, persist its context in Redis, return it."""
    state = secrets.token_urlsafe(32)
    payload = json.dumps({"provider": provider, "code_verifier": code_verifier})
    await RedisClient.set(f"{_STATE_PREFIX}{state}", payload, ttl=STATE_TTL)
    return state


async def consume_state(state: str) -> dict | None:
    """Return the context for ``state`` and invalidate it (single use).

    Returns ``None`` if the state is unknown, expired, or malformed.
    """
    if not state:
        return None
    key = f"{_STATE_PREFIX}{state}"
    raw = await RedisClient.get(key)
    if raw is None:
        return None
    # One-time use: delete immediately so a replayed code can't be reused.
    await RedisClient.delete(key)
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict) or "provider" not in data:
        return None
    return data
