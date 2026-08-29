#!/usr/bin/env python3
"""Safety hook for Kimi Code CLI.

Placed in ~/.kimi-code/hooks/ and referenced from ~/.kimi-code/config.toml:

    [[hooks]]
    event = "PreToolUse"
    matcher = "Bash"
    command = "python3 ~/.kimi-code/hooks/block-main-git-mutations.py"
    timeout = 5

Blocks `git commit` / `git push` / `git merge` when the current branch is
`main` (or `master`). Branch detection uses `git rev-parse --abbrev-ref HEAD`,
which also works inside git worktrees.

The hook receives a JSON payload via stdin. Exit codes:
    0  = allow
    2  = block
    other non-zero / timeout = allow (fail-open)
"""

import json
import re
import subprocess
import sys

PROTECTED_BRANCHES = {"main", "master"}
MUTATION_RE = re.compile(r"\bgit\s+(?:-C\s+\S+\s+)?(?:commit|push|merge)\b")


def _current_branch(cwd: str | None) -> str | None:
    """Return the current branch name, or None if it cannot be determined."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=cwd or None,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        # Fail-open: if we cannot parse the event, do not block.
        return 0

    command = payload.get("tool_input", {}).get("command", "")
    if not isinstance(command, str):
        return 0

    if not MUTATION_RE.search(command):
        return 0

    cwd = payload.get("cwd")
    branch = _current_branch(cwd if isinstance(cwd, str) else None)
    if branch is None:
        # Fail-open: not a git repo or git unavailable — nothing to enforce.
        return 0

    if branch in PROTECTED_BRANCHES:
        print(
            f"Blocked by safety hook: git mutation on protected branch "
            f"'{branch}'. Switch to a feature/bugfix branch (worktree) first: {command}",
            file=sys.stderr,
        )
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
