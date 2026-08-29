#!/usr/bin/env python3
"""Safety hook for Kimi Code CLI.

Placed in ~/.kimi-code/hooks/ and referenced from ~/.kimi-code/config.toml:

    [[hooks]]
    event = "PreToolUse"
    matcher = "Bash"
    command = "python3 ~/.kimi-code/hooks/single-test-run.py"
    timeout = 5

Blocks `make test-backend` / `make test-frontend` when another backend test
run is still alive. Detection uses the same lock file the Makefile wraps
`test-backend` / `test-onec-mock` with (`flock -w 1800`): if the lock cannot
be acquired non-blocking, a run is in progress. This prevents the template
DB race from LESSONS_LEARNED 2026-08-01.

The hook receives a JSON payload via stdin. Exit codes:
    0  = allow
    2  = block
    other non-zero / timeout = allow (fail-open)
"""

import json
import os
import re
import sys

LOCK_PATH = os.environ.get("TEST_BACKEND_LOCK", "/tmp/promelectron-test-backend.lock")
TEST_CMD_RE = re.compile(r"\bmake\b[^;&|]*\btest-(?:backend|frontend)\b")


def _lock_held(lock_path: str) -> bool:
    """Return True if the lock file is currently held by another process."""
    try:
        import fcntl
    except ImportError:
        # Non-POSIX platform: cannot check, fail-open.
        return False
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
    except OSError:
        return False
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return True
        # Acquired: no run in progress. Release immediately.
        fcntl.flock(fd, fcntl.LOCK_UN)
        return False
    finally:
        os.close(fd)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        # Fail-open: if we cannot parse the event, do not block.
        return 0

    command = payload.get("tool_input", {}).get("command", "")
    if not isinstance(command, str):
        return 0

    if not TEST_CMD_RE.search(command):
        return 0

    if _lock_held(LOCK_PATH):
        print(
            f"Blocked by safety hook: another backend test run holds "
            f"{LOCK_PATH}. Wait for it to finish (template DB race, "
            f"LESSONS_LEARNED 2026-08-01): {command}",
            file=sys.stderr,
        )
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
