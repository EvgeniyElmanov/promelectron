#!/usr/bin/env python3
"""
Helper for the /implement pipeline in Promelectron.

Manages task IDs, git worktrees, and review-loop state so that subagents
do not need to remember long Bash sequences.

Usage:
    python scripts/implement-pipeline.py setup "Add promo codes to cart"
    python scripts/implement-pipeline.py worktree-path <task-id>
    python scripts/implement-pipeline.py cleanup <task-id>
"""

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKTREES_ROOT = PROJECT_ROOT / ".worktrees"
AGENT_DIR = PROJECT_ROOT / ".agent"


def slugify(text: str) -> str:
    """Create a short kebab-case task id from description."""
    # Take first 6 words, lower, remove non-alpha-num, join by dash
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())[:6]
    base = "-".join(words) or "task"
    # Append date suffix to reduce collision chance
    suffix = datetime.now().strftime("%m%d")
    return f"{base}-{suffix}"


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=cwd or PROJECT_ROOT,
        check=check,
        capture_output=True,
        text=True,
    )


def cmd_setup(args: argparse.Namespace) -> int:
    description = " ".join(args.description)
    task_id = slugify(description)
    task_dir = AGENT_DIR / task_id
    review_dir = task_dir / "review"
    worktree = WORKTREES_ROOT / f"implement-{task_id}"
    branch = f"feature/{task_id}"

    task_dir.mkdir(parents=True, exist_ok=True)
    review_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    task_file = task_dir / "task.md"
    if not task_file.exists():
        task_file.write_text(
            f"""# Task: {task_id}

## Description
{description}

## Flags
{args.flags or "none"}

## Date
{today}
""",
            encoding="utf-8",
        )

    print(f"TASK_ID={task_id}")
    print(f"TASK_DIR={task_dir}")
    print(f"WORKTREE={worktree}")
    print(f"BRANCH={branch}")
    return 0


def cmd_worktree_path(args: argparse.Namespace) -> int:
    worktree = WORKTREES_ROOT / f"implement-{args.task_id}"
    print(worktree)
    return 0


def cmd_create_worktree(args: argparse.Namespace) -> int:
    task_id = args.task_id
    worktree = WORKTREES_ROOT / f"implement-{task_id}"
    branch = f"feature/{task_id}"
    base_ref = args.base_ref or "HEAD"

    WORKTREES_ROOT.mkdir(parents=True, exist_ok=True)

    # Check if worktree/branch already exists
    result = run(["git", "worktree", "list"], check=False)
    if str(worktree) in result.stdout:
        print(f"Worktree already exists: {worktree}")
        print(worktree)
        return 0

    run(["git", "worktree", "add", str(worktree), "-b", branch, base_ref])
    print(worktree)
    return 0


def cmd_cleanup(args: argparse.Namespace) -> int:
    task_id = args.task_id
    worktree = WORKTREES_ROOT / f"implement-{task_id}"
    branch = f"feature/{task_id}"

    if worktree.exists():
        run(["git", "worktree", "remove", "--force", str(worktree)], check=False)

    # Delete branch if it exists locally
    run(["git", "branch", "-D", branch], check=False)
    run(["git", "worktree", "prune"], check=False)

    print(f"Cleaned up {worktree} and {branch}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Promelectron /implement pipeline helper")
    sub = parser.add_subparsers(dest="command", required=True)

    setup = sub.add_parser("setup", help="Create task directory and generate task-id")
    setup.add_argument("description", nargs="+", help="Feature description")
    setup.add_argument("--flags", default="", help="Flags like --backend-only")

    wt_path = sub.add_parser("worktree-path", help="Print worktree path for task-id")
    wt_path.add_argument("task_id", help="Task ID")

    wt_create = sub.add_parser("create-worktree", help="Create git worktree for task-id")
    wt_create.add_argument("task_id", help="Task ID")
    wt_create.add_argument("--base-ref", default="HEAD", help="Base ref to branch from")

    cleanup = sub.add_parser("cleanup", help="Remove worktree and feature branch")
    cleanup.add_argument("task_id", help="Task ID")

    args = parser.parse_args()

    handlers = {
        "setup": cmd_setup,
        "worktree-path": cmd_worktree_path,
        "create-worktree": cmd_create_worktree,
        "cleanup": cmd_cleanup,
    }

    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
