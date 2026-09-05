#!/usr/bin/env python3
"""
Helper for the /implement pipeline in Promelectron.

Manages task IDs, git worktrees, review-loop state, context size
estimation, and GitHub backlog automation so that subagents do not need
to remember long Bash sequences.

Usage:
    python scripts/implement-pipeline.py setup "Add promo codes to cart"
    python scripts/implement-pipeline.py create-worktree <task-id>
    python scripts/implement-pipeline.py create-issue <task-id>
    python scripts/implement-pipeline.py set-status <task-id> <status>
    python scripts/implement-pipeline.py sync-backlog
    python scripts/implement-pipeline.py check-context <task-id>
    python scripts/implement-pipeline.py cleanup <task-id>
    python scripts/implement-pipeline.py janitor [--days N] [--dry-run]
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
import agent_state  # noqa: E402
from agent_retry import retry_on_kimi_errors  # noqa: E402
from agent_metrics import collect_task_metrics  # noqa: E402

WORKTREES_ROOT = PROJECT_ROOT / ".worktrees"
# Transient per-task pipeline artifacts live under .agent/runs/ (gitignored),
# separate from the committed .agent/ planning dir (BACKLOG.md, PLANNING_HANDOFF.md, ...).
AGENT_RUNS_DIR = PROJECT_ROOT / ".agent" / "runs"
BACKLOG_FILE = PROJECT_ROOT / ".agent" / "BACKLOG.md"

# Context management thresholds for Kimi K3 (1M context window).
# The 600K warning threshold (~60% of the window) leaves room for system
# prompt, reasoning_content, and tool outputs.
# Aligned with .kimi-code/rules/agent-commons.md.
CONTEXT_THRESHOLD = 600_000
CHARS_PER_TOKEN = 4

# GitHub Project configuration for Promelectron.
# Can be overridden via env vars for reuse in forks.
GITHUB_ORG = os.environ.get("GITHUB_ORG", "AutonomaCo")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "promelectron")
DEFAULT_PROJECT_OWNER = os.environ.get("GITHUB_PROJECT_OWNER", "AutonomaCo")
DEFAULT_PROJECT_NUMBER = os.environ.get("GITHUB_PROJECT_NUMBER", "1")
PROJECT_ID = os.environ.get("GITHUB_PROJECT_ID", "PVT_kwDOEOu5sM4BbRfc")
STATUS_FIELD_ID = os.environ.get(
    "GITHUB_STATUS_FIELD_ID", "PVTSSF_lADOEOu5sM4BbRfczhWDIWE"
)
STATUS_OPTIONS = {
    "backlog": os.environ.get("GITHUB_STATUS_BACKLOG_ID", "f75ad846"),
    "ready": os.environ.get("GITHUB_STATUS_READY_ID", "61e4505c"),
    "in-progress": os.environ.get("GITHUB_STATUS_IN_PROGRESS_ID", "47fc9ee4"),
    "in-review": os.environ.get("GITHUB_STATUS_IN_REVIEW_ID", "df73e18b"),
    "done": os.environ.get("GITHUB_STATUS_DONE_ID", "98236657"),
}


def slugify(text: str) -> str:
    """Create a short kebab-case task id from description."""
    # Take first 6 words, lower, remove non-alpha-num, join by dash
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())[:6]
    base = "-".join(words) or "task"
    # Cyrillic-only descriptions yield an empty word list, so every task of
    # the day would collide on the default "task" id. Add a short
    # deterministic hash of the description instead.
    if base == "task":
        base = f"task-{hashlib.sha1(text.encode()).hexdigest()[:6]}"
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


def run_json(cmd: list[str], cwd: Path | None = None) -> dict:
    """Run a command that returns JSON and parse it."""
    result = run(cmd, cwd=cwd, check=True)
    return json.loads(result.stdout or "{}")


def cmd_setup(args: argparse.Namespace) -> int:
    description = " ".join(args.description)
    task_id = slugify(description)
    task_dir = AGENT_RUNS_DIR / task_id
    review_dir = task_dir / "review"
    # Worktree path is just <task-id>, aligned with the .claude pipeline convention.
    worktree = WORKTREES_ROOT / task_id
    branch = f"{args.branch_prefix}/{task_id}"

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


# Images for frontend deps prep in fresh worktrees (see .kimi-code/LESSONS_LEARNED.md, 2026-08-24).
PLAYWRIGHT_IMAGE = "mcr.microsoft.com/playwright:v1.61.0-jammy"
NODE_IMAGE = "node:20-slim"


def _prepare_frontend_deps(worktree: Path) -> None:
    """Install frontend dependencies in a fresh worktree.

    Host `npm ci` misses the optional peer `picomatch` (vite then fails to
    start); the containerised `npm install` in the Playwright image adds it
    but leaves root-owned files in the bind-mounted node_modules, which
    breaks later `--user` runs and worktree removal — fix with a chown pass.
    """
    frontend = worktree / "frontend"
    if not (frontend / "package-lock.json").exists():
        return
    if not shutil.which("npm") or not shutil.which("docker"):
        print("WARNING: npm or docker not found — skipping frontend deps prep, run it manually")
        return
    uid, gid = os.getuid(), os.getgid()
    steps = [
        (["npm", "ci", "--silent"], frontend),
        (["docker", "run", "--rm", "-v", f"{frontend}:/app", "-w", "/app",
          PLAYWRIGHT_IMAGE, "npm", "install", "--silent"], None),
        (["docker", "run", "--rm", "-v", f"{frontend}:/app",
          NODE_IMAGE, "chown", "-R", f"{uid}:{gid}", "/app/node_modules"], None),
    ]
    for cmd, cwd in steps:
        result = run(cmd, cwd=cwd, check=False)
        if result.returncode != 0:
            print(f"WARNING: frontend deps prep failed at '{cmd[0]} {cmd[1]}': {result.stderr.strip()[:300]}")
            return
    print("Frontend dependencies prepared (npm ci + container install + chown).")


@retry_on_kimi_errors(max_attempts=4, backoff_seconds=2.0)
def cmd_create_worktree(args: argparse.Namespace) -> int:
    task_id = args.task_id
    worktree = WORKTREES_ROOT / task_id
    branch = f"{args.branch_prefix}/{task_id}"
    # Always branch from origin/main unless explicitly overridden.
    base_ref = args.base_ref or "origin/main"

    WORKTREES_ROOT.mkdir(parents=True, exist_ok=True)

    # Check if worktree/branch already exists. Parse porcelain output
    # line by line: a substring match would treat ".worktrees/fix-a-0101-extra"
    # as an existing "fix-a-0101" worktree.
    result = run(["git", "worktree", "list", "--porcelain"], check=False)
    existing_paths = {
        line.split(" ", 1)[1]
        for line in result.stdout.splitlines()
        if line.startswith("worktree ")
    }
    if str(worktree) in existing_paths:
        print(f"Worktree already exists: {worktree}")
        if args.prepare_frontend:
            _prepare_frontend_deps(worktree)
        print(worktree)
        return 0

    # If the task branch survived an interrupted run, attach the worktree
    # to it instead of failing on `-b` with "branch already exists".
    branch_exists = run(["git", "branch", "--list", branch], check=False).stdout.strip()
    if branch_exists:
        run(["git", "worktree", "add", str(worktree), branch])
    else:
        run(["git", "worktree", "add", str(worktree), "-b", branch, base_ref])
    if not args.skip_frontend_prep:
        _prepare_frontend_deps(worktree)
    print(worktree)
    return 0


def _remove_tree(path: Path) -> bool:
    """Remove a directory tree, fixing root-owned files via docker chown if needed.

    Returns True when the path is gone afterwards, False (with a loud
    WARNING) otherwise. Never fails silently: callers must not report
    success unless this returns True.
    """
    if not path.exists():
        return True
    try:
        shutil.rmtree(path)
    except OSError as exc:
        print(f"WARNING: rmtree {path} failed ({exc}); trying docker chown fallback")
        if shutil.which("docker"):
            uid, gid = os.getuid(), os.getgid()
            result = run(
                ["docker", "run", "--rm", "-v", f"{path}:/w",
                 NODE_IMAGE, "chown", "-R", f"{uid}:{gid}", "/w"],
                check=False,
            )
            if result.returncode != 0:
                print(f"WARNING: docker chown failed: {result.stderr.strip()[:300]}")
            try:
                shutil.rmtree(path)
            except OSError as exc2:
                print(f"WARNING: rmtree {path} still failing after chown ({exc2})")
        else:
            print("WARNING: docker not found — cannot chown root-owned files")
    if path.exists():
        print(f"WARNING: {path} was NOT removed (leftover files on disk)")
        return False
    return True


def _cleanup_task(task_id: str, branch_prefix: str) -> bool:
    """Remove the task worktree and its branch (idempotent).

    Returns True when the worktree directory is gone afterwards.
    """
    worktree = WORKTREES_ROOT / task_id
    branch = f"{branch_prefix}/{task_id}"

    removed = True
    if worktree.exists():
        run(["git", "worktree", "remove", "--force", str(worktree)], check=False)
        # The dir survives `git worktree remove` when it is not a registered
        # worktree (orphan checkout) or contains files git cannot delete —
        # remove it explicitly instead of silently leaving gigabytes behind.
        removed = _remove_tree(worktree)

    # Delete branch if it exists locally
    run(["git", "branch", "-D", branch], check=False)
    run(["git", "worktree", "prune"], check=False)
    return removed


@retry_on_kimi_errors(max_attempts=4, backoff_seconds=2.0)
def cmd_cleanup(args: argparse.Namespace) -> int:
    task_id = args.task_id
    if not _cleanup_task(task_id, args.branch_prefix):
        print(f"CLEANUP_INCOMPLETE {WORKTREES_ROOT / task_id}")
        return 1
    print(f"Cleaned up {WORKTREES_ROOT / task_id} and {args.branch_prefix}/{task_id}")
    return 0


def _task_age_days(task_dir: Path) -> float:
    """Days since the newest file in the task directory (last activity)."""
    mtimes = [p.stat().st_mtime for p in task_dir.rglob("*") if p.is_file()]
    mtime = max(mtimes) if mtimes else task_dir.stat().st_mtime
    return max(0.0, (time.time() - mtime) / 86400.0)


def cmd_janitor(args: argparse.Namespace) -> int:
    """Remove coordination dirs, worktrees and branches of done tasks older than N days.

    Only tasks whose detected phase is `done` are touched; anything with an
    unreadable state is skipped with a warning and never deleted.
    """
    if not AGENT_RUNS_DIR.exists():
        print("Nothing to do: .agent/runs/ does not exist")
        return 0

    candidates = 0
    for task_dir in sorted(AGENT_RUNS_DIR.iterdir()):
        if not task_dir.is_dir():
            continue
        task_id = task_dir.name
        try:
            state = agent_state.collect_state(task_id)
        except (SystemExit, Exception) as exc:  # unreadable state -> skip, never delete
            print(f"SKIP {task_id}: could not read state ({exc})")
            continue
        if state.phase != "done":
            continue
        age = _task_age_days(task_dir)
        if age < args.days:
            continue
        if args.dry_run:
            print(f"[dry-run] would remove {task_dir}, worktree and feature|bugfix branches ({task_id}, age {age:.1f}d)")
        else:
            removed_dir = _remove_tree(task_dir)
            removed_wt = _cleanup_task(task_id, "feature")
            removed_wt = _cleanup_task(task_id, "bugfix") and removed_wt
            if removed_dir and removed_wt:
                print(f"REMOVED {task_id} (age {age:.1f}d)")
            else:
                print(f"REMOVE_INCOMPLETE {task_id} (age {age:.1f}d) — see WARNINGs above")
        candidates += 1

    print(f"JANITOR_CANDIDATES={candidates} DRY_RUN={int(args.dry_run)}")
    return 0


# ---------------------------------------------------------------------------
# GitHub backlog automation
# ---------------------------------------------------------------------------


def parse_existing_issue(task_text: str) -> str | None:
    """Return issue number if task.md already references a GitHub issue."""
    match = re.search(r"github_issue:\s*#?(\d+)", task_text, re.IGNORECASE)
    if match:
        return match.group(1)
    # Fallback: header-style record, e.g. "## github_issue\n#122 https://..."
    match = re.search(
        r"^#+\s*github_issue\s*\n+\s*(?:-\s*)?#(\d+)",
        task_text,
        re.IGNORECASE | re.MULTILINE,
    )
    return match.group(1) if match else None


def extract_spec_section(spec_text: str, section_name: str) -> str:
    """Extract a section from spec.md by header name."""
    pattern = rf"## {re.escape(section_name)}\s*\n(.*?)(?=\n## |\Z)"
    match = re.search(pattern, spec_text, re.DOTALL | re.IGNORECASE)
    return (match.group(1).strip() if match else "").strip()


def build_issue_body(task_id: str, spec_text: str) -> str:
    """Build a concise GitHub issue body from the approved spec."""
    summary = extract_spec_section(spec_text, "Summary") or extract_spec_section(
        spec_text, "Analysis"
    )
    must_haves = extract_spec_section(spec_text, "Must-haves")
    acceptance = extract_spec_section(spec_text, "Acceptance Criteria")
    out_of_scope = extract_spec_section(spec_text, "Out of Scope")

    parts = [
        f"**Task ID:** `{task_id}`",
        "",
        "## Summary",
        summary or "See full spec below.",
    ]

    if must_haves:
        parts.extend(["", "## Must-haves", must_haves])
    if acceptance:
        parts.extend(["", "## Acceptance Criteria", acceptance])
    if out_of_scope:
        parts.extend(["", "## Out of Scope", out_of_scope])

    parts.extend(
        [
            "",
            "---",
            f"Full spec: `.agent/runs/{task_id}/spec.md`",
        ]
    )
    return "\n".join(parts)


def build_issue_title(spec_text: str, task_description: str) -> str:
    """Build a short issue title from spec or task description."""
    # Try to find a clear title in spec headers.
    for pattern in (r"^# (.+)$", r"## Task Type\s*\n(.+)"):
        match = re.search(pattern, spec_text, re.MULTILINE)
        if match:
            return match.group(1).strip()
    # Fallback to first line of task description.
    return task_description.strip().split("\n")[0][:120]


def gh_issue_exists(issue_number: str) -> bool:
    """Check whether a GitHub issue exists and is accessible."""
    result = run(
        ["gh", "issue", "view", issue_number, "--repo", f"{GITHUB_ORG}/{GITHUB_REPO}"],
        check=False,
    )
    return result.returncode == 0


def create_or_update_issue(title: str, body: str, issue_number: str | None = None) -> str:
    """Create a new issue or update an existing one. Return issue URL."""
    repo = f"{GITHUB_ORG}/{GITHUB_REPO}"
    if issue_number and gh_issue_exists(issue_number):
        run(
            ["gh", "issue", "edit", issue_number, "--repo", repo, "--title", title, "--body", body],
            check=True,
        )
        return f"https://github.com/{GITHUB_ORG}/{GITHUB_REPO}/issues/{issue_number}"

    result = run(
        ["gh", "issue", "create", "--repo", repo, "--title", title, "--body", body],
        check=True,
    )
    return result.stdout.strip()


def add_issue_to_project(issue_url: str) -> str:
    """Add an issue to the GitHub Project. Return project item ID."""
    run(
        [
            "gh",
            "project",
            "item-add",
            DEFAULT_PROJECT_NUMBER,
            "--owner",
            DEFAULT_PROJECT_OWNER,
            "--url",
            issue_url,
        ],
        check=True,
    )
    return find_project_item_id(issue_url)


def find_project_item_id(issue_url: str) -> str:
    """Find the project item ID for a given issue URL."""
    # gh project item-list не пагинирует: один запрос с высоким --limit.
    items = run_json(
        [
            "gh",
            "project",
            "item-list",
            DEFAULT_PROJECT_NUMBER,
            "--owner",
            DEFAULT_PROJECT_OWNER,
            "--format",
            "json",
            "--limit",
            "500",
        ]
    ).get("items", [])
    for item in items:
        content = item.get("content", {})
        if content.get("url") == issue_url:
            return item["id"]
    raise RuntimeError(f"Could not find project item ID for {issue_url}")


def set_project_item_status(item_id: str, status: str) -> None:
    """Set the Status field of a project item."""
    option_id = STATUS_OPTIONS.get(status)
    if not option_id:
        raise ValueError(f"Unknown status: {status}. Use one of {list(STATUS_OPTIONS)}")

    run(
        [
            "gh",
            "project",
            "item-edit",
            "--id",
            item_id,
            "--field-id",
            STATUS_FIELD_ID,
            "--project-id",
            PROJECT_ID,
            "--single-select-option-id",
            option_id,
        ],
        check=True,
    )


def persist_issue_metadata(task_file: Path, issue_number: str, issue_url: str) -> None:
    """Write github_issue metadata back to task.md and spec.md."""
    meta_block = f"\n## GitHub\n- github_issue: #{issue_number}\n- issue_url: {issue_url}\n"
    text = task_file.read_text(encoding="utf-8")
    if "## GitHub" in text:
        text = re.sub(r"\n## GitHub\n.*?(?=\n## |\Z)", meta_block.rstrip(), text, flags=re.DOTALL)
    else:
        text = text.rstrip() + meta_block
    task_file.write_text(text, encoding="utf-8")

    spec_file = task_file.parent / "spec.md"
    if spec_file.exists():
        spec_text = spec_file.read_text(encoding="utf-8")
        if "## GitHub" in spec_text:
            spec_text = re.sub(
                r"\n## GitHub\n.*?(?=\n## |\Z)",
                meta_block.rstrip(),
                spec_text,
                flags=re.DOTALL,
            )
        else:
            spec_text = spec_text.rstrip() + meta_block
        spec_file.write_text(spec_text, encoding="utf-8")


def append_backlog_entry(task_id: str, title: str, issue_number: str) -> None:
    """Append a backlog entry with issue link if not already present."""
    if not BACKLOG_FILE.exists():
        return

    text = BACKLOG_FILE.read_text(encoding="utf-8")
    issue_link = f"https://github.com/{GITHUB_ORG}/{GITHUB_REPO}/issues/{issue_number}"
    if issue_link in text or f"#{issue_number}" in text:
        return

    # Insert before the first section header after the current sprint table.
    entry = (
        f"\n| — | {title} | [#{issue_number}]({issue_link}) | — | P1 | **backlog** | — | — | — |\n"
    )
    BACKLOG_FILE.write_text(text.rstrip() + entry, encoding="utf-8")


@retry_on_kimi_errors(max_attempts=4, backoff_seconds=2.0)
def cmd_create_issue(args: argparse.Namespace) -> int:
    task_id = args.task_id
    task_dir = AGENT_RUNS_DIR / task_id
    task_file = task_dir / "task.md"
    spec_file = task_dir / "spec.md"

    if not task_file.exists():
        print(f"ERROR: task.md not found for {task_id}", file=sys.stderr)
        return 1

    task_text = task_file.read_text(encoding="utf-8")
    existing_issue = parse_existing_issue(task_text) or args.issue

    spec_text = spec_file.read_text(encoding="utf-8") if spec_file.exists() else ""
    title = build_issue_title(spec_text, extract_spec_section(task_text, "Description"))
    body = build_issue_body(task_id, spec_text)

    issue_url = create_or_update_issue(title, body, existing_issue)
    issue_number = issue_url.rstrip("/").split("/")[-1]

    # Add to project and set status.
    item_id = add_issue_to_project(issue_url)
    set_project_item_status(item_id, args.status)

    persist_issue_metadata(task_file, issue_number, issue_url)
    append_backlog_entry(task_id, title, issue_number)

    print(f"ISSUE_URL={issue_url}")
    print(f"ISSUE_NUMBER={issue_number}")
    print(f"PROJECT_ITEM_ID={item_id}")
    print(f"STATUS={args.status}")
    return 0


@retry_on_kimi_errors(max_attempts=4, backoff_seconds=2.0)
def cmd_set_status(args: argparse.Namespace) -> int:
    task_id = args.task_id
    task_file = AGENT_RUNS_DIR / task_id / "task.md"
    if not task_file.exists():
        print(f"ERROR: task.md not found for {task_id}", file=sys.stderr)
        return 1

    task_text = task_file.read_text(encoding="utf-8")
    issue_number = parse_existing_issue(task_text)
    if not issue_number:
        print(f"ERROR: no github_issue found in task.md for {task_id}", file=sys.stderr)
        return 1

    issue_url = f"https://github.com/{GITHUB_ORG}/{GITHUB_REPO}/issues/{issue_number}"
    item_id = find_project_item_id(issue_url)
    set_project_item_status(item_id, args.status)

    print(f"ISSUE_NUMBER={issue_number}")
    print(f"STATUS={args.status}")
    return 0


@retry_on_kimi_errors(max_attempts=4, backoff_seconds=2.0)
def cmd_sync_backlog(args: argparse.Namespace) -> int:
    """One-way sync: update local BACKLOG.md with open issues from GitHub Project."""
    # gh project item-list не пагинирует: один запрос с высоким --limit.
    items = run_json(
        [
            "gh",
            "project",
            "item-list",
            DEFAULT_PROJECT_NUMBER,
            "--owner",
            DEFAULT_PROJECT_OWNER,
            "--format",
            "json",
            "--limit",
            "500",
        ]
    ).get("items", [])

    if not BACKLOG_FILE.exists():
        print(f"ERROR: {BACKLOG_FILE} not found", file=sys.stderr)
        return 1

    text = BACKLOG_FILE.read_text(encoding="utf-8")
    new_entries = []
    for item in items:
        content = item.get("content", {})
        if content.get("type") != "Issue":
            continue
        # Skip completed items; rely on the project board status.
        if item.get("status") in {"Done", "Closed"}:
            continue
        issue_number = content.get("number")
        title = content.get("title", "Untitled")
        url = content.get("url", "")
        if not issue_number or url in text or f"#{issue_number}" in text:
            continue
        new_entries.append(f"| — | {title} | [#{issue_number}]({url}) | — | P1 | **backlog** | — | — | — |")

    if new_entries:
        BACKLOG_FILE.write_text(
            text.rstrip() + "\n" + "\n".join(new_entries) + "\n",
            encoding="utf-8",
        )

    print(f"SYNCED={len(new_entries)}")
    return 0


@retry_on_kimi_errors(max_attempts=4, backoff_seconds=2.0)
def cmd_record_metrics(args: argparse.Namespace) -> int:
    """Collect metrics for a task and write them to .agent/runs/<task-id>/metrics.json."""
    import json

    task_id = args.task_id
    metrics = collect_task_metrics(task_id)
    metrics_file = AGENT_RUNS_DIR / task_id / "metrics.json"
    metrics_file.write_text(
        json.dumps(metrics.__dict__, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"METRICS_FILE={metrics_file}")
    print(f"ESTIMATED_TOKENS={metrics.estimated_tokens}")
    print(f"REVIEW_ITERATIONS={metrics.review_iterations}")
    print(f"QA_ITERATIONS={metrics.qa_iterations}")
    print(f"REACHED_PR={int(metrics.reached_pr)}")
    print(f"COMPLETED={int(metrics.completed)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Promelectron /implement pipeline helper")
    sub = parser.add_subparsers(dest="command", required=True)

    setup = sub.add_parser("setup", help="Create task directory and generate task-id")
    setup.add_argument("description", nargs="+", help="Feature description")
    setup.add_argument("--flags", default="", help="Flags like --backend-only")
    setup.add_argument(
        "--branch-prefix",
        choices=["feature", "bugfix"],
        default="feature",
        help="Prefix for the task branch (default: feature)",
    )

    wt_path = sub.add_parser("worktree-path", help="Print worktree path for task-id")
    wt_path.add_argument("task_id", help="Task ID")

    check_context = sub.add_parser("check-context", help="Estimate task context size in tokens")
    check_context.add_argument("task_id", help="Task ID")

    wt_create = sub.add_parser("create-worktree", help="Create git worktree for task-id")
    wt_create.add_argument("task_id", help="Task ID")
    wt_create.add_argument("--base-ref", default="origin/main", help="Base ref to branch from (default: origin/main)")
    wt_create.add_argument(
        "--branch-prefix",
        choices=["feature", "bugfix"],
        default="feature",
        help="Prefix for the task branch (default: feature)",
    )
    wt_create.add_argument(
        "--skip-frontend-prep",
        action="store_true",
        help="Do not install frontend dependencies after creating the worktree",
    )
    wt_create.add_argument(
        "--prepare-frontend",
        action="store_true",
        help="Re-run frontend deps prep for an already existing worktree",
    )

    cleanup = sub.add_parser("cleanup", help="Remove worktree and task branch")
    cleanup.add_argument("task_id", help="Task ID")
    cleanup.add_argument(
        "--branch-prefix",
        choices=["feature", "bugfix"],
        default="feature",
        help="Prefix of the task branch to delete (default: feature)",
    )

    janitor = sub.add_parser(
        "janitor",
        help="Remove .agent/runs dirs, worktrees and branches of done tasks older than N days",
    )
    janitor.add_argument("--days", type=int, default=14, help="Age threshold in days (default: 14)")
    janitor.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print what would be removed, delete nothing",
    )

    issue_create = sub.add_parser(
        "create-issue",
        help="Create or update a GitHub Issue for a task and add it to the project",
    )
    issue_create.add_argument("task_id", help="Task ID")
    issue_create.add_argument("--issue", default=None, help="Existing issue number to link/update")
    issue_create.add_argument(
        "--status",
        default="in-progress",
        choices=list(STATUS_OPTIONS),
        help="Project board status to set after adding the issue",
    )

    status_set = sub.add_parser(
        "set-status",
        help="Update the GitHub Project status for a task's linked issue",
    )
    status_set.add_argument("task_id", help="Task ID")
    status_set.add_argument(
        "status",
        choices=list(STATUS_OPTIONS),
        help="Target project board status",
    )

    sub.add_parser(
        "sync-backlog",
        help="Sync open GitHub Project issues into docs/backlog.md",
    )

    record_metrics = sub.add_parser(
        "record-metrics",
        help="Collect and save agent pipeline metrics for a task",
    )
    record_metrics.add_argument("task_id", help="Task ID")

    args = parser.parse_args()

    handlers = {
        "setup": cmd_setup,
        "worktree-path": cmd_worktree_path,
        "check-context": cmd_check_context,
        "create-worktree": cmd_create_worktree,
        "cleanup": cmd_cleanup,
        "janitor": cmd_janitor,
        "create-issue": cmd_create_issue,
        "set-status": cmd_set_status,
        "sync-backlog": cmd_sync_backlog,
        "record-metrics": cmd_record_metrics,
    }

    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
