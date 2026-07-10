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
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from agent_retry import retry_on_kimi_errors  # noqa: E402
from agent_metrics import collect_task_metrics  # noqa: E402

WORKTREES_ROOT = PROJECT_ROOT / ".worktrees"
# Transient per-task pipeline artifacts live under .agent/runs/ (gitignored),
# separate from the committed .agent/ planning dir (BACKLOG.md, PLANNING_HANDOFF.md, ...).
AGENT_RUNS_DIR = PROJECT_ROOT / ".agent" / "runs"
BACKLOG_FILE = PROJECT_ROOT / ".agent" / "BACKLOG.md"

# Context management thresholds for Kimi K2.7 (256K context window).
# We use a conservative threshold to leave room for system prompt,
# reasoning_content, and tool outputs.
# Aligned with .kimi-code/rules/agent-commons.md.
CONTEXT_THRESHOLD = 150_000
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


@retry_on_kimi_errors(max_attempts=4, backoff_seconds=2.0)
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


@retry_on_kimi_errors(max_attempts=4, backoff_seconds=2.0)
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


# ---------------------------------------------------------------------------
# GitHub backlog automation
# ---------------------------------------------------------------------------


def parse_existing_issue(task_text: str) -> str | None:
    """Return issue number if task.md already references a GitHub issue."""
    match = re.search(r"github_issue:\s*#?(\d+)", task_text, re.IGNORECASE)
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
        new_entries.append(f"| — | [#{issue_number}]({url}) | {title} | — |")

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

    wt_path = sub.add_parser("worktree-path", help="Print worktree path for task-id")
    wt_path.add_argument("task_id", help="Task ID")

    check_context = sub.add_parser("check-context", help="Estimate task context size in tokens")
    check_context.add_argument("task_id", help="Task ID")

    wt_create = sub.add_parser("create-worktree", help="Create git worktree for task-id")
    wt_create.add_argument("task_id", help="Task ID")
    wt_create.add_argument("--base-ref", default="origin/main", help="Base ref to branch from (default: origin/main)")

    cleanup = sub.add_parser("cleanup", help="Remove worktree and feature branch")
    cleanup.add_argument("task_id", help="Task ID")

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
        help="Sync open GitHub Project issues into .agent/BACKLOG.md",
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
        "create-issue": cmd_create_issue,
        "set-status": cmd_set_status,
        "sync-backlog": cmd_sync_backlog,
        "record-metrics": cmd_record_metrics,
    }

    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
