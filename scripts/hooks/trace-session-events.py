#!/usr/bin/env python3
"""Session-event trace hook for Kimi Code CLI.

Placed in ~/.kimi-code/hooks/ and referenced from ~/.kimi-code/config.toml:

    [[hooks]]
    event = "TaskStarted"
    command = "python3 ~/.kimi-code/hooks/trace-session-events.py"
    timeout = 5

Appends lifecycle events (TaskStarted, TurnStarted, ...) as JSON lines to
`.agent/hook-events.jsonl` in the workspace root, so scripts/agent_state.py
and plan-maintainer improve-loops can correlate background task runs.

Writes only when the workspace looks like the Promelectron repo (has an
`.agent/` directory); in every other project the hook is a silent no-op.
Always fails open: exit 0 whatever happens.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

MAX_LOG_BYTES = 5_000_000


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    cwd = payload.get("cwd")
    root = Path(cwd) if isinstance(cwd, str) else Path(os.getcwd())
    agent_dir = root / ".agent"
    if not agent_dir.is_dir():
        return 0

    log_path = agent_dir / "hook-events.jsonl"
    try:
        if log_path.exists() and log_path.stat().st_size > MAX_LOG_BYTES:
            log_path.replace(agent_dir / "hook-events.1.jsonl")
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "hook": payload.get("event") or payload.get("hook_event_name"),
            "payload": payload,
        }
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
