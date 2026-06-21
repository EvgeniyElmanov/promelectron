#!/usr/bin/env python3
"""Safety hook for Kimi Code CLI.

Placed in ~/.kimi-code/hooks/ and referenced from ~/.kimi-code/config.toml:

    [[hooks]]
    event = "PreToolUse"
    matcher = "Bash"
    command = "python3 ~/.kimi-code/hooks/block-dangerous-bash.py"
    timeout = 5

The hook receives a JSON payload via stdin. Exit codes:
    0  = allow
    2  = block
    other non-zero / timeout = allow (fail-open)
"""

import json
import re
import sys


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        # Fail-open: if we cannot parse the event, do not block.
        return 0

    command = payload.get("tool_input", {}).get("command", "")
    if not isinstance(command, str):
        return 0

    # Patterns are case-insensitive and allow optional whitespace.
    forbidden_patterns = [
        # rm -rf on absolute paths (rm -rf /, rm -rf /home, etc.)
        r"rm\s+-rf\s+/",
        # SQL destructive operations
        r"\bDROP\s+",
        r"\bTRUNCATE\s+",
        # Force push
        r"git\s+push\s+.*--force",
        r"git\s+push\s+-f\b",
        # Direct main push should still go through explicit approval,
        # even if a permission rule allows it in some modes.
        r"git\s+push\s+origin\s+main\b",
    ]

    for pattern in forbidden_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            print(
                f"Blocked by safety hook (pattern: {pattern!r}): {command}",
                file=sys.stderr,
            )
            return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
