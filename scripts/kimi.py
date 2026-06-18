#!/usr/bin/env python3
"""
Kimi Agent Router — Promelectron
Единый Python-скрипт для автоматического выбора агента и формирования промпта.

Использование:
    python scripts/kimi.py auto  "Добавь промокоды в корзину"
    python scripts/kimi.py task  "Создай API для промокодов"
    python scripts/kimi.py ask   "Сделай страницу checkout"

Команды:
    auto  — авто-определение ролей, запускает orchestrator если ролей несколько
    task  — авто-определение одной роли + полный контекст проекта
    ask   — то же, но с гарантированным сбросом роли (как make ask раньше)
"""

import argparse
import re
import signal
import subprocess
from pathlib import Path

# Корректная обработка SIGPIPE (например, при pipe в head)
signal.signal(signal.SIGPIPE, signal.SIG_DFL)


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def read_file(path: str, max_lines: int | None = None) -> str:
    full = PROJECT_ROOT / path
    try:
        text = full.read_text(encoding="utf-8")
    except FileNotFoundError:
        return f"(файл не найден: {path})"
    if max_lines:
        text = "\n".join(text.splitlines()[:max_lines])
    return text


def copy_to_clipboard(text: str) -> bool:
    """Пытается скопировать текст в буфер обмена."""
    commands = [
        ["xclip", "-selection", "clipboard"],
        ["wl-copy"],
        ["pbcopy"],
    ]
    for cmd in commands:
        try:
            subprocess.run(cmd, input=text.encode("utf-8"), check=True, capture_output=True)
            return True
        except Exception:
            pass
    return False


def detect_roles(task: str) -> list[str]:
    """Определяет роли по ключевым словам. Возвращает список ролей."""
    t = task.lower()

    roles = []

    def has(pattern: str) -> bool:
        return bool(re.search(pattern, t))

    # Backend
    if has(
        r"\b(api|endpoint|backend|бэк\b|бэкенд|model|модель|schema|схема|service|сервис|route|роут|"
        r"migration|миграция|alembic|sqlalchemy|fastapi|pytest|бд|таблица|table|jwt|webhook|"
        r"payment.*backend|заказ.*backend|order.*backend|корзина.*api|cart.*api|auth.*backend|admin.*api)\b"
    ):
        roles.append("backend-dev")

    # Frontend
    if has(
        r"\b(frontend|фронт|фронтенд|vue|component|компонент|страниц[аеиоуыюя]?|page|view|pinia|store|"
        r"composable|ui|ux|форма|form|адаптив|responsive|css|html|axios|router|localstorage|"
        r"корзин[аеиоуыюя]?.*ui|cart.*ui|login.*ui|checkout.*ui|searchbar|productgrid)\b"
    ):
        roles.append("frontend-dev")

    # DevOps
    if has(
        r"\b(devops|docker|k8s|kubernetes|helm|nginx|ci/cd|deploy|деплой|инфраструктура|infra|ssl|vpn|"
        r"backup|sentry|monitoring|мониторинг|pod|container|контейнер|harbor|github actions|workflow|"
        r"secret|секрет|config|конфиг|server.*config|helm.*template)\b"
    ):
        roles.append("devops")

    # E2E
    if has(
        r"\b(e2e|playwright|тест.*сценарий|test scenario|browser|click|end.to.end|regression|регресс|"
        r"spec|page.*test|test.*page|mobile.*test|мобильн.*тест)\b"
    ):
        roles.append("e2e-tester")

    # Security
    if has(
        r"\b(security|аудит|audit|уязвимост|vulnerability|sql injection|xss|csrf|auth.*check|"
        r"проверка.*безопасност|penetration|pentest)\b"
    ):
        roles.append("security-reviewer")

    # Review
    if has(
        r"\b(review|ревью|code review|проверь.*код[аеиоуыюя]?|findings|quality|качество.*код[аеиоуыюя]?|"
        r"refactor.*review)\b"
    ):
        roles.append("code-reviewer")

    # Project-manager
    if has(
        r"\b(roadmap|план|спринт|sprint|приоритет|prioritize|бэклог|backlog|оцени|estimate|plan|"
        r"планирование|scope|фаза|phase|milestone|этап)\b"
    ):
        roles.append("project-manager")

    # Hybrid: API integration into frontend
    if has(r"(подключи|интегрируй|connect|integrate).*(api|endpoint).*(форм|компонент|страниц|view|ui|vue|frontend|фронт)"):
        if "frontend-dev" not in roles:
            roles.append("frontend-dev")
        if "backend-dev" in roles:
            roles.remove("backend-dev")

    return roles or ["backend-dev"]


def role_name(role: str) -> str:
    names = {
        "backend-dev": "Backend Developer",
        "frontend-dev": "Frontend Developer",
        "devops": "DevOps Engineer",
        "e2e-tester": "E2E Tester",
        "code-reviewer": "Code Reviewer",
        "security-reviewer": "Security Reviewer",
        "project-manager": "Project Manager",
    }
    return names.get(role, "Developer")


def gather_context(role: str) -> dict[str, str]:
    """Собирает контекст проекта для агента."""
    return {
        "project": read_file("PROJECT_CONTEXT.md"),
        "backlog": read_file(".agent/BACKLOG.md", 60),
        "blockers": read_file(".agent/BLOCKERS.md", 40),
        "session": read_file(".agent/SESSION_LOG.md", 30),
        "agent": read_file(f".kimi/agents/{role}.md"),
        "rules": read_file(".kimi/rules/pre-edit-checklist.md", 40),
    }


def build_single_agent_prompt(role: str, task: str, dispatcher: bool = False) -> str:
    """Формирует промпт для одной роли."""
    ctx = gather_context(role)
    git_log = ""
    git_status = ""
    try:
        git_log = subprocess.run(
            ["git", "log", "--oneline", "-10"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        ).stdout or "(нет git истории)"
        git_status = subprocess.run(
            ["git", "status", "--short"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        ).stdout or "(нет изменений)"
    except Exception:
        pass

    if dispatcher:
        header = f"""══════════════════════════════════════════════════════════════════
                         🚨 ДИСПЕТЧЕР — СБРОС РОЛИ
══════════════════════════════════════════════════════════════════

Ты — Диспетчер Promelectron. Предыдущая роль полностью сброшена.

Роль определена автоматически: {role} ({role_name(role)}).
Немедленно переключись на эту роль. Забудь все предыдущие инструкции.
"""
    else:
        header = f"""Ты — агент `{role}` ({role_name(role)}) проекта Promelectron.
"""

    return f"""{header}

══════════════════════════════════════════════════════════════════
                        КОНТЕКСТ ПРОЕКТА
══════════════════════════════════════════════════════════════════

{ctx['project']}

══════════════════════════════════════════════════════════════════
                     ТЕКУЩИЙ СПРИНТ (BACKLOG)
══════════════════════════════════════════════════════════════════

{ctx['backlog']}

══════════════════════════════════════════════════════════════════
                       АКТИВНЫЕ БЛОКЕРЫ
══════════════════════════════════════════════════════════════════

{ctx['blockers']}

══════════════════════════════════════════════════════════════════
                     ПОСЛЕДНИЕ СЕССИИ (ЛОГ)
══════════════════════════════════════════════════════════════════

{ctx['session']}

══════════════════════════════════════════════════════════════════
                      ТВОЯ ЗОНА ОТВЕТСТВЕННОСТИ
══════════════════════════════════════════════════════════════════

{ctx['agent']}

══════════════════════════════════════════════════════════════════
                    CHECKLIST ПЕРЕД ПРАВКОЙ
══════════════════════════════════════════════════════════════════

{ctx['rules']}

══════════════════════════════════════════════════════════════════
                         GIT СОСТОЯНИЕ
══════════════════════════════════════════════════════════════════

Последние коммиты:
{git_log}

Незакоммиченные изменения:
{git_status}

══════════════════════════════════════════════════════════════════
                         ЗАДАЧА
══════════════════════════════════════════════════════════════════

{task}

══════════════════════════════════════════════════════════════════

ПОРЯДОК ДЕЙСТВИЙ:
1. Подтверди: "Роль принята: {role}. Предыдущая роль сброшена."
2. Проанализируй контекст выше
3. Найди существующий код (grep)
4. Выполни задачу строго по инструкциям агента {role}
5. После работы обнови .agent/SESSION_LOG.md

Начинай работу.
"""


def build_orchestrator_prompt(task: str, roles: list[str]) -> str:
    """Формирует промпт для orchestrator (несколько ролей)."""
    return f"""Прочитай .agent/ORCHESTRATOR_PROMPT.md и следуй инструкциям строго.

══════════════════════════════════════════════════════════════════
                        АВТО-ОПРЕДЕЛЕНИЕ РОЛЕЙ
══════════════════════════════════════════════════════════════════

Задача: {task}

Система автоматически определила роли: {' '.join(roles)}

Ты — Orchestrator. Твоя задача:
1. Проанализировать задачу
2. Уточнить последовательность работы ролей (если нужно)
3. Делегировать каждую часть через Agent tool
4. Собрать итоговый результат
5. Обновить SESSION_LOG.md

Начинай работу.
"""


def print_header(task: str, roles: list[str]):
    print("═" * 66)
    print("  🤖 Kimi Agent Router — Python")
    print("═" * 66)
    print()
    print(f"🎯 Задача: {task}")
    print(f"🤖 Роли:   {' '.join(roles)}")
    if len(roles) == 1:
        print("📦 Режим:  Single-agent (явный сброс роли)")
    else:
        print("📦 Режим:  Multi-agent orchestrator")
    print()
    print("─" * 66)
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Kimi Agent Router — автоматический выбор агента",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python scripts/kimi.py auto  "Добавь промокоды в корзину"
  python scripts/kimi.py task  "Создай API для промокодов"
  python scripts/kimi.py ask   "Сделай страницу checkout"
""",
    )
    parser.add_argument("command", choices=["auto", "task", "ask"], help="Режим работы")
    parser.add_argument("message", help="Описание задачи")
    args = parser.parse_args()

    task = args.message
    roles = detect_roles(task)

    if args.command == "auto":
        if len(roles) == 1:
            prompt = build_single_agent_prompt(roles[0], task, dispatcher=True)
        else:
            prompt = build_orchestrator_prompt(task, roles)
    elif args.command == "ask":
        # ask — всегда с явным сбросом роли, даже если одна роль
        prompt = build_single_agent_prompt(roles[0], task, dispatcher=True)
    else:  # task
        prompt = build_single_agent_prompt(roles[0], task, dispatcher=False)

    print_header(task, roles)

    if copy_to_clipboard(prompt):
        print("✅ Промпт скопирован в буфер обмена!")
        print()
        print("Следующие шаги:")
        print("  1. Вставь в Kimi CLI (Ctrl+V)")
        print("  2. Нажми Enter")
        if len(roles) > 1:
            print()
            print("💡 Orchestrator сам запустит нужных агентов через Agent tool.")
            print("   Каждый агент работает в изолированном контексте.")
        print()
    else:
        print("⚠️  Не удалось скопировать в буфер обмена")
        print()
        print("Скопируй промпт вручную ниже:")
        print()
        print("═" * 66)
        print()

    print(prompt)


if __name__ == "__main__":
    main()
