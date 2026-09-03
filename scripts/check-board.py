#!/usr/bin/env python3
"""Проверка целостности пульта запуска.

Пульт (ai-launcher/BOARD.md) — витрина открытых GitHub Issues, а промпты
(ai-launcher/prompts/) — то, чем эти пункты запускаются. Всё это правится руками,
несколькими агентами, в разных сессиях — и расходится тихо: якорь задваивается и
кнопка молча ведёт не туда, промпт остаётся без issue, issue не знает про свой промпт.

Скрипт ловит ровно эти расхождения. Запускается перед коммитом борда и из CI.

    python3 scripts/check-board.py            # форма борда + связки промпт↔issue
    python3 scripts/check-board.py --offline  # без обращений к GitHub

Код возврата: 0 — чисто, 1 — есть расхождения.
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys

REPO = "AutonomaCo/promelectron"
ROOT = pathlib.Path(__file__).resolve().parent.parent
BOARD = ROOT / "ai-launcher" / "BOARD.md"
PROMPTS = ROOT / "ai-launcher" / "prompts"

problems: list[str] = []
notes: list[str] = []


def fail(msg: str) -> None:
    problems.append(msg)


def check_board_form(text: str) -> set[str]:
    """Форма пульта: якоря, ссылки, разделители, кнопки."""
    anchors = re.findall(r'id="(i-\d+)"', text)
    dupes = sorted({a for a in anchors if anchors.count(a) > 1})
    if dupes:
        fail(f"задвоенные якоря (кнопка молча уведёт не туда): {', '.join(dupes)}")

    links = set(re.findall(r"\]\(#(i-\d+)\)", text))
    dangling = sorted(links - set(anchors))
    if dangling:
        fail(f"ссылки Указателя в никуда: {', '.join(dangling)}")

    prev = ""
    for line in text.split("\n"):
        if re.match(r'^> (<a id="i-\d+"></a>|✅ \*\*#\d+\*\*)', line):
            if prev != "---" and not prev.startswith("# "):
                fail(f"пункт без разделителя `---` перед ним: {line[:60]}")
            anchor = re.search(r'id="i-(\d+)"', line)
            if anchor and f"/issues/{anchor.group(1)}" not in line:
                fail(
                    f"пункт #{anchor.group(1)}: в заголовке нет ссылки на GitHub — "
                    "с борда не попасть в обсуждение"
                )
        if line.strip():
            prev = line

    return set(anchors)


def check_prompts(text: str) -> dict[str, str]:
    """Кнопки ↔ файлы промптов. Возвращает {номер issue: имя файла промпта}."""
    on_disk = {p.name for p in PROMPTS.glob("*.prompt.txt")} if PROMPTS.is_dir() else set()
    used = set(re.findall(r"PROMPT=ai-launcher/prompts/([\w.-]+)", text))

    for missing in sorted(used - on_disk):
        fail(f"кнопка ссылается на несуществующий промпт: {missing}")
    for orphan in sorted(on_disk - used):
        fail(f"промпт есть, а кнопки на борде нет: {orphan} (пункт невидим для /sessions)")

    mapping: dict[str, str] = {}
    for name in on_disk:
        m = re.match(r"^[a-z0-9-]+_(\d+)-", name)
        if not m:
            fail(f"имя промпта не по форме `<замок>_<issue#>-<слаг>.prompt.txt`: {name}")
            continue
        mapping[m.group(1)] = name
    return mapping


def check_issue_links(mapping: dict[str, str]) -> None:
    """Каждый промпт ссылается на свой issue, и наоборот."""
    for number, name in sorted(mapping.items()):
        body = (PROMPTS / name).read_text(encoding="utf-8")
        if not re.search(rf"[Ii]ssue #{number}\b", body):
            fail(f"{name}: в промпте не назван issue #{number} — из него не найти обсуждение")

    if "--offline" in sys.argv:
        notes.append("--offline: связка «issue → промпт» на GitHub не проверялась")
        return

    for number, name in sorted(mapping.items()):
        run = subprocess.run(
            ["gh", "issue", "view", number, "--repo", REPO, "--json", "body,state,title"],
            capture_output=True, text=True,
        )
        if run.returncode != 0:
            notes.append(f"issue #{number} не прочитан ({run.stderr.strip()[:60]}) — связка не проверена")
            continue
        data = json.loads(run.stdout)
        if data["state"] != "OPEN":
            fail(f"промпт {name} ведёт на ЗАКРЫТЫЙ issue #{number} «{data['title'][:40]}»")
        if name not in (data["body"] or ""):
            fail(f"issue #{number}: в теле нет блока «Запуск» с промптом {name}")


def main() -> int:
    if not BOARD.exists():
        print(f"нет файла борда: {BOARD}", file=sys.stderr)
        return 1

    text = BOARD.read_text(encoding="utf-8")
    check_board_form(text)
    check_issue_links(check_prompts(text))

    for note in notes:
        print(f"  · {note}")
    if problems:
        print(f"\n✗ Расхождений: {len(problems)}")
        for p in problems:
            print(f"  – {p}")
        print("\nПравила и порядок починки — ai-launcher/CONVENTIONS.md")
        return 1
    print("✓ Пульт согласован: форма, кнопки, связки промпт↔issue")
    return 0


if __name__ == "__main__":
    sys.exit(main())
