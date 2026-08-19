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
        r"git\s+push\s+origin\s+master\b",
        # Push of the current HEAD to main/master (git push origin HEAD:main)
        r"git\s+push\b[^;&|]*\bHEAD\s*:\s*(main|master)\b",
        # Bare "git push" with no remote/refspec: upstream may be main.
        r"git\s+push\s*(?:$|[;&|])",
    ]

    for pattern in forbidden_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            print(
                f"Blocked by safety hook (pattern: {pattern!r}): {command}",
                file=sys.stderr,
            )
            return 2

    if _is_dangerous_rm(command):
        print(
            f"Blocked by safety hook (dangerous rm): {command}",
            file=sys.stderr,
        )
        return 2

    return 0


def _is_dangerous_rm(command: str) -> bool:
    """Detect rm with recursive+force flags (any order/long forms) on
    dangerous targets (/, ~, $HOME, /*).

    Catches bypasses of the plain `rm -rf /` regex: `rm -fr /`,
    `rm -r -f ~`, `rm --recursive --force $HOME`, etc.
    """
    dangerous_roots = {"", "~", "$HOME"}
    for segment in re.split(r"[;&|]", command):
        tokens = segment.split()
        if "rm" not in tokens:
            continue
        args = tokens[tokens.index("rm") + 1:]
        flags = [t for t in args if t.startswith("-")]
        targets = [t for t in args if not t.startswith("-")]

        def _has(short: str, long_: str) -> bool:
            return any(
                t == long_
                or (t.startswith("-") and not t.startswith("--") and short in t[1:])
                for t in flags
            )

        has_recursive = _has("r", "--recursive") or _has("R", "--recursive")
        has_force = _has("f", "--force")
        if not (has_recursive and has_force):
            continue
        for target in targets:
            stripped = target.strip("'\"")
            if stripped == "/*" or stripped.rstrip("/") in dangerous_roots:
                return True
    return False


if __name__ == "__main__":
    sys.exit(main())
