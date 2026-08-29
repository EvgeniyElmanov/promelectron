#!/usr/bin/env python3
"""
Typed state + observability для агентского пайплайна Promelectron.

Единый источник истины для:
- детекции фазы пайплайна задачи (tracker → architect → dev → reviewer → qa_gate → mr → done);
- typed-снимка состояния (artifacts, findings, tests, PR);
- append-only trace событий в `.agent/runs/<task-id>/trace.jsonl`
  с correlation ID на всю задачу (observability: кто/когда/что).

Usage:
    python scripts/agent_state.py state <task-id>                          # полный снимок JSON
    python scripts/agent_state.py phase <task-id>                          # только фаза
    python scripts/agent_state.py trace <task-id> <event> [--actor NAME] [--data '{}']
    python scripts/agent_state.py history <task-id>                        # весь trace.jsonl

Скиллы (`flow-*`, `implement`, `fix`, `qa-gate`, `ship`) должны вызывать
этот скрипт вместо собственного парсинга артефактов.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AGENT_RUNS_DIR = PROJECT_ROOT / ".agent" / "runs"

TASK_ID_RE = re.compile(r"^[a-z0-9-]+$")

PHASES = ["tracker", "architect", "dev", "reviewer", "qa_gate", "mr", "done"]


@dataclass(frozen=True)
class FindingsSummary:
    total: int = 0
    open: int = 0
    fixed: int = 0        # FIXED + RESOLVED — ждут re-review
    verified: int = 0
    approved: bool = False  # верхнеуровневый вердикт файла


@dataclass(frozen=True)
class TaskState:
    task_id: str
    phase: str
    artifacts: list[str] = field(default_factory=list)
    branch: str | None = None
    worktree_exists: bool = False
    findings: FindingsSummary = field(default_factory=FindingsSummary)
    tests_status: str | None = None   # TESTS_PASSED | TESTS_FAILED | None
    pr_state: str | None = None       # OPEN | MERGED | CLOSED | None
    pr_url: str | None = None
    correlation_id: str | None = None
    updated_at: str = ""


@dataclass(frozen=True)
class TraceEvent:
    ts: str
    task_id: str
    correlation_id: str
    event: str
    actor: str = "orchestrator"
    data: dict = field(default_factory=dict)


def _validate_task_id(task_id: str) -> None:
    if not TASK_ID_RE.match(task_id):
        print(f"ERROR: invalid task-id '{task_id}' (expected ^[a-z0-9-]+$)", file=sys.stderr)
        sys.exit(2)


def _run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(PROJECT_ROOT), *args],
        capture_output=True, text=True, timeout=15,
    )
    return result.stdout.strip()


def _find_branch(task_id: str) -> str | None:
    for prefix in ("feature/", "bugfix/"):
        if _run_git("branch", "--list", f"{prefix}{task_id}"):
            return f"{prefix}{task_id}"
    return None


def _pr_ref_from_task_md(agent_dir: Path) -> str | None:
    """pr_url из task.md — fallback, когда локальная ветка уже удалена после merge."""
    task_md = agent_dir / "task.md"
    if not task_md.exists():
        return None
    try:
        text = task_md.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    match = re.search(r"pr_url:\s*(https?://\S+)", text, re.IGNORECASE)
    return match.group(1) if match else None


def _find_pr(branch: str | None) -> tuple[str | None, str | None]:
    """Best-effort PR lookup; любые ошибки (нет gh, нет сети) -> (None, None)."""
    if not branch:
        return None, None
    try:
        result = subprocess.run(
            ["gh", "pr", "view", branch, "--json", "state,url"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return None, None
        payload = json.loads(result.stdout)
        return payload.get("state"), payload.get("url")
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError, OSError):
        return None, None


def _find_pr_by_head(task_id: str) -> tuple[str | None, str | None]:
    """PR по head-ветке feature|bugfix/<task-id>; работает и после удаления ветки."""
    for prefix in ("feature/", "bugfix/"):
        try:
            result = subprocess.run(
                ["gh", "pr", "list", "--state", "all", "--head",
                 f"{prefix}{task_id}", "--json", "state,url", "--limit", "1"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0:
                continue
            payload = json.loads(result.stdout)
            if payload:
                return payload[0].get("state"), payload[0].get("url")
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError, OSError):
            return None, None
    return None, None


def _parse_findings(findings_file: Path) -> FindingsSummary:
    if not findings_file.exists():
        return FindingsSummary()
    text = findings_file.read_text(encoding="utf-8", errors="replace")
    head = "\n".join(text.splitlines()[:20])
    return FindingsSummary(
        total=len(re.findall(r"^### \[", text, flags=re.MULTILINE)),
        open=len(re.findall(r"Status:\*\*\s*OPEN\b", text)),
        fixed=len(re.findall(r"Status:\*\*\s*(?:FIXED|RESOLVED)\b", text)),
        verified=len(re.findall(r"Status:\*\*\s*VERIFIED\b", text)),
        approved=bool(re.search(r"Status:\*\*\s*APPROVED\b", head)),
    )


def _parse_tests(test_findings_file: Path) -> str | None:
    if not test_findings_file.exists():
        return None
    text = test_findings_file.read_text(encoding="utf-8", errors="replace")
    matches = re.findall(r"TESTS_PASSED|TESTS_FAILED", text)
    return matches[-1] if matches else None


def _read_correlation_id(trace_file: Path) -> str | None:
    if not trace_file.exists():
        return None
    try:
        with trace_file.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    return json.loads(line).get("correlation_id")
    except (json.JSONDecodeError, OSError):
        return None
    return None


def _trace_has_event(agent_dir: Path, event_name: str) -> bool:
    """Return True if the task trace contains the given event."""
    trace_file = agent_dir / "trace.jsonl"
    if not trace_file.exists():
        return False
    try:
        for line in trace_file.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                if json.loads(line).get("event") == event_name:
                    return True
            except json.JSONDecodeError:
                continue
    except OSError:
        return False
    return False


def detect_phase(
    agent_dir: Path,
    findings: FindingsSummary,
    tests_status: str | None,
    pr_state: str | None,
) -> str:
    if pr_state == "MERGED":
        return "done"
    # `mr` — только когда PR реально существует (или был открыт: событие в trace);
    # прогон тестов без PR означает лишь пройденный QA gate.
    if pr_state == "OPEN" or _trace_has_event(agent_dir, "pr_opened"):
        return "mr"
    if findings.approved or tests_status == "TESTS_PASSED":
        return "qa_gate"
    if (agent_dir / "review" / "findings.md").exists():
        return "reviewer"
    if (agent_dir / "spec.md").exists():
        return "dev"
    if (agent_dir / "task.md").exists():
        return "architect"
    return "tracker"


def collect_state(task_id: str, with_pr: bool = True) -> TaskState:
    _validate_task_id(task_id)
    agent_dir = AGENT_RUNS_DIR / task_id
    artifacts: list[str] = []
    if agent_dir.exists():
        artifacts = sorted(
            str(p.relative_to(agent_dir)) for p in agent_dir.rglob("*") if p.is_file()
        )
    branch = _find_branch(task_id)
    pr_state, pr_url = None, None
    if with_pr:
        # 1) локальная ветка (быстрый путь); 2) pr_url из task.md;
        # 3) head-ветка на GitHub — работает и после удаления ветки при cleanup.
        pr_state, pr_url = _find_pr(branch)
        if pr_state is None:
            pr_state, pr_url = _find_pr(_pr_ref_from_task_md(agent_dir))
        if pr_state is None:
            pr_state, pr_url = _find_pr_by_head(task_id)
    findings = _parse_findings(agent_dir / "review" / "findings.md")
    tests_status = _parse_tests(agent_dir / "review" / "test-findings.md")
    return TaskState(
        task_id=task_id,
        phase=detect_phase(agent_dir, findings, tests_status, pr_state),
        artifacts=artifacts,
        branch=branch,
        worktree_exists=(PROJECT_ROOT / ".worktrees" / task_id).exists(),
        findings=findings,
        tests_status=tests_status,
        pr_state=pr_state,
        pr_url=pr_url,
        correlation_id=_read_correlation_id(agent_dir / "trace.jsonl"),
        updated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def append_trace(task_id: str, event: str, actor: str, data: dict) -> TraceEvent:
    _validate_task_id(task_id)
    agent_dir = AGENT_RUNS_DIR / task_id
    agent_dir.mkdir(parents=True, exist_ok=True)
    trace_file = agent_dir / "trace.jsonl"
    correlation_id = _read_correlation_id(trace_file) or uuid.uuid4().hex[:12]
    record = TraceEvent(
        ts=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        task_id=task_id,
        correlation_id=correlation_id,
        event=event,
        actor=actor,
        data=data,
    )
    with trace_file.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_state = sub.add_parser("state", help="полный снимок состояния задачи (JSON)")
    p_state.add_argument("task_id")
    p_state.add_argument("--no-pr", action="store_true", help="не дёргать gh pr view (offline)")

    p_phase = sub.add_parser("phase", help="только текущая фаза")
    p_phase.add_argument("task_id")
    p_phase.add_argument("--no-pr", action="store_true")

    p_trace = sub.add_parser("trace", help="добавить событие в trace.jsonl")
    p_trace.add_argument("task_id")
    p_trace.add_argument("event")
    p_trace.add_argument("--actor", default="orchestrator")
    p_trace.add_argument("--data", default="{}", help="JSON-объект с доп. полями")

    p_history = sub.add_parser("history", help="вывести весь trace задачи")
    p_history.add_argument("task_id")

    args = parser.parse_args()

    if args.command == "state":
        state = collect_state(args.task_id, with_pr=not args.no_pr)
        print(json.dumps(asdict(state), ensure_ascii=False, indent=2))
    elif args.command == "phase":
        state = collect_state(args.task_id, with_pr=not args.no_pr)
        print(state.phase)
    elif args.command == "trace":
        try:
            data = json.loads(args.data)
        except json.JSONDecodeError:
            print(f"ERROR: --data is not valid JSON: {args.data}", file=sys.stderr)
            sys.exit(2)
        record = append_trace(args.task_id, args.event, args.actor, data)
        print(json.dumps(asdict(record), ensure_ascii=False))
    elif args.command == "history":
        _validate_task_id(args.task_id)
        trace_file = AGENT_RUNS_DIR / args.task_id / "trace.jsonl"
        if not trace_file.exists():
            print(f"no trace for {args.task_id}")
            return
        print(trace_file.read_text(encoding="utf-8"), end="")


if __name__ == "__main__":
    main()
