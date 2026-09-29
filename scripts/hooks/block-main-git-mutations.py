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

The harness always reports the *session* cwd in the payload, not the tool's
`cwd` argument, so the hook resolves the target directory from the command
itself: an explicit `git -C <dir>` before the mutation verb, or a leading
`cd <dir> &&` chain. Only when neither is present does it fall back to the
payload cwd.

The hook receives a JSON payload via stdin. Exit codes:
    0  = allow
    2  = block
    other non-zero / timeout = allow (fail-open)
"""

import json
import os
import re
import subprocess
import sys

PROTECTED_BRANCHES = {"main", "master"}
MUTATION_RE = re.compile(
    r"\bgit\s+(?:-C\s+(?P<gitdir>\"[^\"]+\"|'[^']+'|\S+)\s+)?(?:commit|push|merge)\b"
)
CD_PREFIX_RE = re.compile(r"^\s*cd\s+(?P<dir>\"[^\"]+\"|'[^']+'|\S+)\s*&&")


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


def _unquote(path: str) -> str:
    if len(path) >= 2 and path[0] == path[-1] and path[0] in {'"', "'"}:
        return path[1:-1]
    return path


def _resolve_target_dir(command: str, payload_cwd: str | None) -> str | None:
    """Directory whose branch the mutation will run on."""
    mutation = MUTATION_RE.search(command)
    if mutation is None:
        return None
    target = mutation.group("gitdir")
    if target is None:
        cd = CD_PREFIX_RE.match(command)
        if cd is not None:
            target = cd.group("dir")
    if target is None:
        return payload_cwd
    target = _unquote(target)
    if not os.path.isabs(target) and isinstance(payload_cwd, str):
        target = os.path.join(payload_cwd, target)
    return target


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        # Fail-open: if we cannot parse the event, do not block.
        return 0

    command = payload.get("tool_input", {}).get("command", "")
    if not isinstance(command, str):
        return 0

    cwd = payload.get("cwd")
    target_dir = _resolve_target_dir(command, cwd if isinstance(cwd, str) else None)
    if target_dir is None:
        return 0

    branch = _current_branch(target_dir)
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
