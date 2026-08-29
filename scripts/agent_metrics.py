#!/usr/bin/env python3
"""
Сбор и агрегация метрик агентского пайплайна Promelectron.

Анализирует артефакты задачи в `.agent/runs/<task-id>/`:
- объём контекста (оценка токенов),
- количество итераций code review,
- количество QA-итераций,
- наличие PR / issue / завершения задачи,
- время жизни задачи.

Usage:
    python scripts/agent_metrics.py <task-id>
    python scripts/agent_metrics.py --all
    python scripts/agent_metrics.py --format=json <task-id>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AGENT_RUNS_DIR = PROJECT_ROOT / ".agent" / "runs"
SESSION_LOG_FILE = PROJECT_ROOT / ".agent" / "SESSION_LOG.md"

# Conservative ratio for mixed Latin/Cyrillic text.
CHARS_PER_TOKEN = 4


@dataclass(frozen=True)
class TaskMetrics:
    task_id: str
    description: str = ""
    flags: str = ""
    created_date: str | None = None
    estimated_tokens: int = 0
    review_iterations: int = 0
    qa_iterations: int = 0
    context_summary_generated: bool = False
    has_spec: bool = False
    github_issue: str | None = None
    github_pr: str | None = None
    reached_pr: bool = False
    completed: bool = False
    lifetime_days: float | None = None


def _parse_task_md(task_file: Path) -> dict[str, str | None]:
    """Parse lightweight metadata from task.md."""
    data: dict[str, str | None] = {
        "description": "",
        "flags": "",
        "created_date": None,
        "github_issue": None,
        "github_pr": None,
    }
    if not task_file.exists():
        return data

    text = task_file.read_text(encoding="utf-8")

    # First line after '# Task:' or first header.
    desc_match = re.search(r"## Description\s*\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
    if desc_match:
        data["description"] = " ".join(desc_match.group(1).strip().split())

    flags_match = re.search(r"## Flags\s*\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
    if flags_match:
        data["flags"] = flags_match.group(1).strip()

    date_match = re.search(r"## Date\s*\n(\d{4}-\d{2}-\d{2})", text)
    if date_match:
        data["created_date"] = date_match.group(1)

    issue_match = re.search(r"github_issue:\s*#?(\d+)", text, re.IGNORECASE)
    if issue_match:
        data["github_issue"] = issue_match.group(1)

    pr_match = re.search(r"pr_url:\s*(https?://\S+)", text, re.IGNORECASE)
    if pr_match:
        data["github_pr"] = pr_match.group(1)

    return data


def _parse_spec_md(spec_file: Path) -> dict[str, str | None]:
    """Parse metadata from spec.md."""
    data: dict[str, str | None] = {"github_issue": None, "github_pr": None}
    if not spec_file.exists():
        return data

    text = spec_file.read_text(encoding="utf-8")

    issue_match = re.search(r"github_issue:\s*#?(\d+)", text, re.IGNORECASE)
    if issue_match:
        data["github_issue"] = issue_match.group(1)

    pr_match = re.search(r"pr_url:\s*(https?://\S+)", text, re.IGNORECASE)
    if pr_match:
        data["github_pr"] = pr_match.group(1)

    return data


def estimate_tokens(task_dir: Path) -> int:
    """Estimate tokens across all markdown artifacts in the task directory."""
    if not task_dir.exists():
        return 0

    total_chars = 0
    for path in task_dir.rglob("*.md"):
        if path.is_file():
            try:
                total_chars += len(path.read_text(encoding="utf-8"))
            except OSError:
                continue
    return (total_chars + CHARS_PER_TOKEN - 1) // CHARS_PER_TOKEN


def count_review_iterations(task_dir: Path) -> int:
    """Count review iterations.

    Primary source — `review_verdict` events in trace.jsonl (findings.md is
    overwritten on every iteration, so counting findings files is wrong).
    Fallback: the max `**Iteration:** N` marker in findings*.md; last
    resort — 1 if any findings file exists, else 0.
    """
    trace_file = task_dir / "trace.jsonl"
    if trace_file.exists():
        iterations = 0
        for line in trace_file.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("event") == "review_verdict":
                iterations += 1
        if iterations:
            return iterations

    review_dir = task_dir / "review"
    if review_dir.exists():
        max_iteration = 0
        has_findings = False
        for path in review_dir.iterdir():
            if not (path.is_file() and path.suffix == ".md"):
                continue
            if "findings" not in path.name.lower() or "test-findings" in path.name.lower():
                continue
            has_findings = True
            text = path.read_text(encoding="utf-8", errors="replace")
            for match in re.finditer(r"\*\*Iteration:\*\*\s*(\d+)", text):
                max_iteration = max(max_iteration, int(match.group(1)))
        if max_iteration:
            return max_iteration
        if has_findings:
            return 1
    return 0


def count_qa_iterations(task_dir: Path) -> int:
    """Count QA iteration files (test-findings*.md) in review/ or qa/."""
    count = 0
    for subdir in (task_dir / "review", task_dir / "qa"):
        if not subdir.exists():
            continue
        for path in subdir.iterdir():
            if path.is_file() and path.suffix == ".md" and "test-findings" in path.name.lower():
                count += 1
    return count


def context_summary_generated(task_dir: Path) -> bool:
    """Return True if CONTEXT_SUMMARY.md exists."""
    return (task_dir / "CONTEXT_SUMMARY.md").exists()


def _scan_session_log_for_task(task_id: str) -> dict[str, bool]:
    """Scan SESSION_LOG.md for PR/completion markers for this task."""
    result = {"reached_pr": False, "completed": False}
    if not SESSION_LOG_FILE.exists():
        return result

    text = SESSION_LOG_FILE.read_text(encoding="utf-8")
    # Find the most recent block for this task-id.
    # Blocks are separated by "=======\n  Следующий шаг:" or by date headers.
    # We search for the task-id and look for PR/completion keywords nearby.
    for match in re.finditer(rf"### \d{{4}}-\d{{2}}-\d{{2}}.*{re.escape(task_id)}", text):
        start = match.start()
        end = text.find("=======", start)
        if end == -1:
            end = len(text)
        block = text[start:end]

        if re.search(r"pr_url|Pull Request|PR #|Merged|merged|merge", block, re.IGNORECASE):
            result["reached_pr"] = True
        if re.search(r"merged|заверш|complete|done|✅ все проверки", block, re.IGNORECASE):
            result["completed"] = True

    return result


def _lifetime_days(created_date: str | None, completed: bool) -> float | None:
    """Return days between created_date and now or last session log mention."""
    if not created_date:
        return None
    try:
        created = datetime.strptime(created_date, "%Y-%m-%d")
    except ValueError:
        return None

    # If completed, we do not have a precise completion date from task files;
    # use today as an upper-bound estimate. Callers may refine via session log.
    now = datetime.now()
    return max(0.0, (now - created).total_seconds() / 86400.0)


def collect_task_metrics(task_id: str) -> TaskMetrics:
    """Collect all metrics for a single task."""
    task_dir = AGENT_RUNS_DIR / task_id
    if not task_dir.exists():
        raise FileNotFoundError(f"Task directory not found: {task_dir}")

    task_meta = _parse_task_md(task_dir / "task.md")
    spec_meta = _parse_spec_md(task_dir / "spec.md")

    issue = task_meta.get("github_issue") or spec_meta.get("github_issue")
    pr = task_meta.get("github_pr") or spec_meta.get("github_pr")

    session_state = _scan_session_log_for_task(task_id)
    reached_pr = bool(pr) or session_state["reached_pr"]
    completed = session_state["completed"]

    created_date = task_meta.get("created_date")
    lifetime = _lifetime_days(created_date, completed)

    return TaskMetrics(
        task_id=task_id,
        description=task_meta.get("description") or "",
        flags=task_meta.get("flags") or "",
        created_date=created_date,
        estimated_tokens=estimate_tokens(task_dir),
        review_iterations=count_review_iterations(task_dir),
        qa_iterations=count_qa_iterations(task_dir),
        context_summary_generated=context_summary_generated(task_dir),
        has_spec=(task_dir / "spec.md").exists(),
        github_issue=issue,
        github_pr=pr,
        reached_pr=reached_pr,
        completed=completed,
        lifetime_days=lifetime,
    )


def collect_all_metrics() -> list[TaskMetrics]:
    """Collect metrics for every task directory under .agent/runs/."""
    if not AGENT_RUNS_DIR.exists():
        return []

    metrics: list[TaskMetrics] = []
    for path in sorted(AGENT_RUNS_DIR.iterdir()):
        if path.is_dir():
            try:
                metrics.append(collect_task_metrics(path.name))
            except FileNotFoundError:
                continue
    return metrics


def _serialize(metrics: TaskMetrics | Iterable[TaskMetrics]) -> dict | list[dict]:
    if isinstance(metrics, TaskMetrics):
        return asdict(metrics)
    return [asdict(m) for m in metrics]


def format_kv(metrics: TaskMetrics) -> str:
    """Format metrics as key=value lines for shell parsing."""
    lines = [
        f"TASK_ID={metrics.task_id}",
        f"ESTIMATED_TOKENS={metrics.estimated_tokens}",
        f"REVIEW_ITERATIONS={metrics.review_iterations}",
        f"QA_ITERATIONS={metrics.qa_iterations}",
        f"HAS_SPEC={int(metrics.has_spec)}",
        f"CONTEXT_SUMMARY={int(metrics.context_summary_generated)}",
        f"GITHUB_ISSUE={metrics.github_issue or ''}",
        f"GITHUB_PR={metrics.github_pr or ''}",
        f"REACHED_PR={int(metrics.reached_pr)}",
        f"COMPLETED={int(metrics.completed)}",
        f"LIFETIME_DAYS={metrics.lifetime_days if metrics.lifetime_days is not None else ''}",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Promelectron agent pipeline metrics")
    parser.add_argument("task_id", nargs="?", help="Task ID to analyze")
    parser.add_argument("--all", action="store_true", help="Analyze all tasks in .agent/runs/")
    parser.add_argument("--format", choices=["kv", "json"], default="kv", help="Output format")

    args = parser.parse_args()

    if args.all:
        metrics = collect_all_metrics()
        if args.format == "json":
            print(json.dumps(_serialize(metrics), ensure_ascii=False, indent=2))
        else:
            for m in metrics:
                print(format_kv(m))
                print()
        return 0

    if not args.task_id:
        parser.error("Provide a task-id or use --all")

    metrics = collect_task_metrics(args.task_id)
    if args.format == "json":
        print(json.dumps(_serialize(metrics), ensure_ascii=False, indent=2))
    else:
        print(format_kv(metrics))
    return 0


if __name__ == "__main__":
    sys.exit(main())
