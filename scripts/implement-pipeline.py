#!/usr/bin/env python3
"""
Helper for the /implement pipeline in Promelectron.

Manages task IDs, git worktrees, review-loop state, and context size
estimation so that subagents do not need to remember long Bash sequences.

Usage:
    python scripts/implement-pipeline.py setup "Add promo codes to cart"
    python scripts/implement-pipeline.py worktree-path <task-id>
    python scripts/implement-pipeline.py check-context <task-id>
    python scripts/implement-pipeline.py cleanup <task-id>
"""

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from agent_retry import retry_on_kimi_errors  # noqa: E402

WORKTREES_ROOT = PROJECT_ROOT / ".worktrees"
# Transient per-task pipeline artifacts live under .agent/runs/ (gitignored),
# separate from the committed .agent/ planning dir (BACKLOG.md, PLANNING_HANDOFF.md, ...).
AGENT_RUNS_DIR = PROJECT_ROOT / ".agent" / "runs"

# Context management thresholds for Kimi K2.7 (256K context window).
# We use a conservative threshold to leave room for system prompt,
# reasoning_content, and tool outputs.
CONTEXT_THRESHOLD = 180_000
CHARS_PER_TOKEN = 4


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
    task_dir = AGENT_RUNS_DIR / task_id
    review_dir = task_dir / "review"
    # Worktree path is just <task-id>, aligned with the .claude pipeline convention.
    worktree = WORKTREES_ROOT / task_id
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


def estimate_context_tokens(task_dir: Path) -> int:
    """Rough estimate of tokens in task artifacts.

    Uses a conservative chars-per-token ratio suitable for mixed
    Latin/Cyrillic text. Returns 0 if the task directory does not exist.
    """
    if not task_dir.exists():
        return 0

    total_chars = 0
    for path in task_dir.rglob("*.md"):
        if path.is_file():
            try:
                total_chars += len(path.read_text(encoding="utf-8"))
            except OSError:
                continue
    # Round up to be conservative.
    return (total_chars + CHARS_PER_TOKEN - 1) // CHARS_PER_TOKEN


def write_context_summary(task_dir: Path) -> Path | None:
    """Generate a compressed CONTEXT_SUMMARY.md if context is large.

    Returns the path to the summary file if it was generated, otherwise None.
    """
    tokens = estimate_context_tokens(task_dir)
    if tokens < CONTEXT_THRESHOLD:
        return None

    summary_file = task_dir / "CONTEXT_SUMMARY.md"
    findings_file = task_dir / "review" / "findings.md"
    spec_file = task_dir / "spec.md"

    summary_parts = [
        f"# Context Summary for {task_dir.name}\n",
        f"\nEstimated tokens: {tokens} (threshold: {CONTEXT_THRESHOLD})\n",
        "\nThis file is a compressed view. Read the full files only when needed.\n",
    ]

    if spec_file.exists():
        spec_text = spec_file.read_text(encoding="utf-8")
        summary_parts.append("\n## Spec Overview\n")
        # Extract key sections from spec.
        for section in ("## Decisions", "## Must-haves", "## Acceptance Criteria"):
            start = spec_text.find(section)
            if start == -1:
                continue
            end = spec_text.find("\n## ", start + 1)
            chunk = spec_text[start:end] if end != -1 else spec_text[start:]
            summary_parts.append(chunk[:2000])
            summary_parts.append("\n")

    if findings_file.exists():
        findings_text = findings_file.read_text(encoding="utf-8")
        summary_parts.append("\n## Open Findings\n")
        # Collect open findings.
        for match in re.finditer(
            r"### \[(F\d+)\].*?\n- \*\*Status:\*\* OPEN.*?(?=\n### \[F\d+\]|\Z)",
            findings_text,
            re.DOTALL,
        ):
            summary_parts.append(match.group(0)[:1500])
            summary_parts.append("\n")

    summary_file.write_text("\n".join(summary_parts), encoding="utf-8")
    return summary_file


def cmd_check_context(args: argparse.Namespace) -> int:
    task_dir = AGENT_RUNS_DIR / args.task_id
    tokens = estimate_context_tokens(task_dir)
    print(f"ESTIMATED_TOKENS={tokens}")
    print(f"THRESHOLD={CONTEXT_THRESHOLD}")
    if tokens >= CONTEXT_THRESHOLD:
        summary = write_context_summary(task_dir)
        if summary:
            print(f"CONTEXT_SUMMARY={summary}")
    return 0


def cmd_worktree_path(args: argparse.Namespace) -> int:
    worktree = WORKTREES_ROOT / args.task_id
    print(worktree)
    return 0


@retry_on_kimi_errors(max_attempts=3, backoff_seconds=2.0)
def cmd_create_worktree(args: argparse.Namespace) -> int:
    task_id = args.task_id
    worktree = WORKTREES_ROOT / task_id
    branch = f"feature/{task_id}"
    # Always branch from origin/main unless explicitly overridden.
    base_ref = args.base_ref or "origin/main"

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


@retry_on_kimi_errors(max_attempts=3, backoff_seconds=2.0)
def cmd_cleanup(args: argparse.Namespace) -> int:
    task_id = args.task_id
    worktree = WORKTREES_ROOT / task_id
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

    check_context = sub.add_parser("check-context", help="Estimate task context size in tokens")
    check_context.add_argument("task_id", help="Task ID")

    wt_create = sub.add_parser("create-worktree", help="Create git worktree for task-id")
    wt_create.add_argument("task_id", help="Task ID")
    wt_create.add_argument("--base-ref", default="origin/main", help="Base ref to branch from (default: origin/main)")

    cleanup = sub.add_parser("cleanup", help="Remove worktree and feature branch")
    cleanup.add_argument("task_id", help="Task ID")

    args = parser.parse_args()

    handlers = {
        "setup": cmd_setup,
        "worktree-path": cmd_worktree_path,
        "check-context": cmd_check_context,
        "create-worktree": cmd_create_worktree,
        "cleanup": cmd_cleanup,
    }

    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
