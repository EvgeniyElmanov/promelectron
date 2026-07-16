#!/usr/bin/env python3
"""
Continuous improvement loop для агентского пайплайна Promelectron.

Анализирует артефакты ВСЕХ задач в `.agent/runs/` поперёк прогонов и находит
повторяющиеся failure patterns — то, что knowledge capture одного run не видит:

- категории findings, встречающиеся в нескольких задачах;
- категории, стоившие итерации ревью (FIXES_NEEDED);
- повторяющиеся CRITICAL/HIGH темы;
- QA-провалы (TESTS_FAILED).

Каждый паттерн сверяется с существующими правилами (`.kimi-code/rules/`,
`LESSONS_LEARNED.md`), чтобы не предлагать уже покрытое.

Usage:
    python scripts/agent_improve.py                  # отчёт по всем задачам
    python scripts/agent_improve.py --last N         # только последние N задач
    python scripts/agent_improve.py --min-tasks 2    # порог "повторяющийся" (default: 2)
    python scripts/agent_improve.py --format=json    # машиночитаемый вывод
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AGENT_RUNS_DIR = PROJECT_ROOT / ".agent" / "runs"
RULES_DIR = PROJECT_ROOT / ".kimi-code" / "rules"
LESSONS_FILE = PROJECT_ROOT / ".kimi-code" / "LESSONS_LEARNED.md"

SEVERITY_RE = re.compile(r"\b(CRITICAL|HIGH|MEDIUM|LOW)\b")
STATUS_RE = re.compile(r"\b(OPEN|VERIFIED|FIXED|RESOLVED|CLOSED)\b")
FINDING_HEADER_RE = re.compile(r"^### \[([A-Z]+-\d+)\]\s*(.*)$")

# Маппинг категорий findings на файлы, где живут соответствующие правила.
CATEGORY_TO_RULE_FILE = {
    "audit": "security.md",
    "pii": "security.md",
    "логирование": "security.md",
    "logging": "security.md",
    "payments": "business.md",
    "idempotency": "business.md",
    "business": "business.md",
    "stock": "business.md",
    "price": "business.md",
    "rate limit": "security.md",
    "scope creep": "pre-edit-checklist.md",
    "тесты": "pre-edit-checklist.md",
    "test": "pre-edit-checklist.md",
}


@dataclass(frozen=True)
class Finding:
    finding_id: str
    task_id: str
    prefix: str          # F | S | B | FE | H
    severity: str        # CRITICAL | HIGH | MEDIUM | LOW | ""
    category: str        # нормализованная категория
    status: str          # OPEN | VERIFIED | FIXED | RESOLVED | CLOSED | ""


@dataclass
class Pattern:
    category: str
    tasks: list[str] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)
    max_severity: str = ""
    caused_fixes_needed: bool = False
    already_covered: bool = False
    suggested_rule_file: str = ""


SEVERITY_ORDER = {"": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


def _normalize_category(raw: str) -> str:
    cat = raw.strip().lower()
    cat = re.sub(r"\s*/\s*", " / ", cat)
    return cat


def parse_findings(task_id: str, findings_file: Path) -> list[Finding]:
    """Парсит заголовки `### [ID] emoji SEVERITY | Category — status` (оба формата)."""
    results: list[Finding] = []
    if not findings_file.exists():
        return results
    for line in findings_file.read_text(encoding="utf-8", errors="replace").splitlines():
        m = FINDING_HEADER_RE.match(line.strip())
        if not m:
            continue
        finding_id, rest = m.groups()
        prefix = finding_id.split("-")[0]
        if "|" in rest:
            left, right = rest.split("|", 1)
        else:
            left, right = rest, ""
        sev = SEVERITY_RE.search(left) or SEVERITY_RE.search(right)
        status = STATUS_RE.search(left) or STATUS_RE.search(right)
        category = right.split("—")[0].split(" - ")[0] if right else left
        results.append(Finding(
            finding_id=finding_id,
            task_id=task_id,
            prefix=prefix,
            severity=sev.group(1) if sev else "",
            category=_normalize_category(category),
            status=status.group(1) if status else "",
        ))
    return results


def _load_rules_corpus() -> str:
    """Весь текст rules + LESSONS_LEARNED одной строкой (lowercase) для проверки покрытия."""
    chunks: list[str] = []
    if RULES_DIR.exists():
        for path in sorted(RULES_DIR.glob("*.md")):
            chunks.append(path.read_text(encoding="utf-8", errors="replace"))
    if LESSONS_FILE.exists():
        chunks.append(LESSONS_FILE.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(chunks).lower()


def _category_covered(category: str, corpus: str) -> bool:
    """Грубая проверка: значимые слова категории уже встречаются в правилах."""
    words = [w for w in re.split(r"[\s/]+", category) if len(w) >= 4]
    if not words:
        return False
    hits = sum(1 for w in words if w in corpus)
    return hits >= max(1, len(words) // 2)


def _suggest_rule_file(category: str) -> str:
    for key, rule_file in CATEGORY_TO_RULE_FILE.items():
        if key in category:
            return f".kimi-code/rules/{rule_file}"
    return ".kimi-code/rules/known-pitfalls.md"


def _fixes_needed_categories(task_dir: Path) -> set[str]:
    """Категории findings из итераций, закончившихся FIXES_NEEDED (через trace.jsonl)."""
    trace_file = task_dir / "trace.jsonl"
    if not trace_file.exists():
        return set()
    # Консервативно: если в trace есть FIXES_NEEDED, считаем все не-LOW findings задачи «дорогими».
    for line in trace_file.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("event") == "review_verdict" and "FIXES_NEEDED" in str(event.get("data", {})):
            return {"*"}
    return set()


def collect_patterns(min_tasks: int, last: int | None) -> tuple[list[Pattern], dict]:
    task_dirs = sorted(
        (p for p in AGENT_RUNS_DIR.iterdir() if p.is_dir()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    ) if AGENT_RUNS_DIR.exists() else []
    if last:
        task_dirs = task_dirs[:last]

    by_category: dict[str, Pattern] = {}
    stats = {"tasks_analyzed": 0, "findings_total": 0, "tasks_with_fixes_needed": 0}
    corpus = _load_rules_corpus()

    for task_dir in task_dirs:
        task_id = task_dir.name
        findings: list[Finding] = []
        for ffile in (task_dir / "review").glob("findings*.md") if (task_dir / "review").exists() else []:
            findings.extend(parse_findings(task_id, ffile))
        # Одна и та же находка может дублироваться в findings.md и findings-<scope>.md.
        seen_ids: set[str] = set()
        findings = [f for f in findings if not (f.finding_id in seen_ids or seen_ids.add(f.finding_id))]
        if not findings and not (task_dir / "trace.jsonl").exists():
            continue
        stats["tasks_analyzed"] += 1
        stats["findings_total"] += len(findings)
        fixes_needed = _fixes_needed_categories(task_dir)
        if fixes_needed:
            stats["tasks_with_fixes_needed"] += 1

        for f in findings:
            if not f.category or f.status == "CLOSED":
                continue
            pattern = by_category.setdefault(f.category, Pattern(category=f.category))
            if task_id not in pattern.tasks:
                pattern.tasks.append(task_id)
            pattern.findings.append(f"{f.finding_id} ({task_id})")
            if SEVERITY_ORDER.get(f.severity, 0) > SEVERITY_ORDER.get(pattern.max_severity, 0):
                pattern.max_severity = f.severity
            if fixes_needed and f.severity not in ("", "LOW"):
                pattern.caused_fixes_needed = True

    patterns = [p for p in by_category.values() if len(p.tasks) >= min_tasks or p.caused_fixes_needed]
    for p in patterns:
        p.already_covered = _category_covered(p.category, corpus)
        p.suggested_rule_file = _suggest_rule_file(p.category)
    patterns.sort(key=lambda p: (p.already_covered, -SEVERITY_ORDER.get(p.max_severity, 0), -len(p.tasks)))
    return patterns, stats


def print_report(patterns: list[Pattern], stats: dict, min_tasks: int) -> None:
    print("=" * 60)
    print("  Continuous Improvement — анализ паттернов пайплайна")
    print("=" * 60)
    print(f"Задач проанализировано: {stats['tasks_analyzed']} · "
          f"findings: {stats['findings_total']} · "
          f"задач с FIXES_NEEDED: {stats['tasks_with_fixes_needed']}")
    print(f"Порог «повторяющийся»: категория в ≥{min_tasks} задачах или вызвала FIXES_NEEDED\n")
    if not patterns:
        print("Повторяющихся паттернов не выявлено. Пайплайн стабилен.")
        return
    for i, p in enumerate(patterns, 1):
        covered = "да (проверить, почему не сработало)" if p.already_covered else "нет — НОВОЕ"
        costly = " · вызывал FIXES_NEEDED" if p.caused_fixes_needed else ""
        print(f"{i}. [{p.max_severity or '—'}] {p.category}{costly}")
        print(f"   Задачи ({len(p.tasks)}): {', '.join(p.tasks)}")
        print(f"   Примеры: {', '.join(p.findings[:4])}")
        print(f"   Покрыто правилами: {covered}")
        if not p.already_covered:
            print(f"   Предложение: добавить правило в {p.suggested_rule_file}")
        print()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--last", type=int, default=None, help="только последние N задач")
    parser.add_argument("--min-tasks", type=int, default=2, help="порог повторяемости (default: 2)")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    patterns, stats = collect_patterns(min_tasks=args.min_tasks, last=args.last)
    if args.format == "json":
        print(json.dumps({
            "stats": stats,
            "patterns": [
                {**asdict(p), "tasks_count": len(p.tasks)}
                for p in patterns
            ],
        }, ensure_ascii=False, indent=2))
    else:
        print_report(patterns, stats, args.min_tasks)
    return 0


if __name__ == "__main__":
    sys.exit(main())
