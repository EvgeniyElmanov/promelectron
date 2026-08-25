---
name: flow-implement
description: >
  Pipeline visualizer for /skill:implement in Promelectron.
  Detects the current phase of a task (Tracker → Architect → Dev → Reviewer → QA Gate → PR → Done)
  from the coordination plane (.agent/runs/<task-id>/) and git state, then renders the
  Mermaid pipeline diagram (шаблон встроен в этот skill; каноническая drawio-диаграмма —
  docs/08-ai-agent-pipeline.drawio) with completed/current phases highlighted.
  Read-only: never edits code, never moves the project board.
type: prompt
whenToUse: When the user asks where a task is in the pipeline, what phase an implement task is at, what the next step is, or wants a visual pipeline status.
arguments: "[task-id] (optional — defaults to the current feature/bugfix branch)"
disableModelInvocation: false
---

# /skill:flow-implement — Визуализатор пайплайна implement

> **ЯЗЫК / LANGUAGE:** Пользователь общается на русском. Все ответы пользователю и артефакты пиши на русском. Стремись рассуждать на русском, но если reasoning уходит на английский — это не ошибка. Код, команды, идентификаторы, пути и технические термины оставляй в оригинале.

Покажи пользователю, **на какой фазе пайплайна `/skill:implement` находится задача**, в виде Mermaid-диаграммы с подсветкой (Mermaid рендерится в web chat Kimi Code) плюс краткий статус и следующее действие.

Это **read-only** скилл: ничего не редактируй, не запускай тесты, не двигай GitHub Project board.

---

## Step 0: Определение task-id

Если `task-id` передан аргументом — используй его. Иначе выведи из текущей ветки:

```bash
git branch --show-current   # feature/<task-id> или bugfix/<task-id>
```

Если ветка `main` и аргумент не передан — перечисли доступные задачи и спроси, какую показать:

```bash
ls .agent/runs/
```

`task-id` должен соответствовать `^[a-z0-9-]+$`. Иначе — остановись и попроси корректный id.

---

## Step 1: Сбор состояния

Используй единый источник истины — `scripts/agent_state.py`:

```bash
python3 scripts/agent_state.py state <task-id>
```

Он вернёт JSON: `phase`, `artifacts`, `branch`, `worktree_exists`, `findings` (total/open/fixed/verified/approved), `tests_status`, `pr_state`, `pr_url`. Флаг `--no-pr` — если gh недоступен/офлайн.

Не падай, если артефактов нет — отсутствие артефакта это тоже сигнал фазы.

---

## Step 2: Определение текущей фазы

Фазу возвращает `agent_state.py` (поле `phase`). Логика детекции (справочно, не дублируй её парсингом):

| Фаза | Признак |
|------|---------|
| `done` | PR существует и `state == MERGED` |
| `mr` | PR открыт (`OPEN`), либо `test-findings.md` содержит `TESTS_PASSED` |
| `qa_gate` | `findings.md` содержит верхнеуровневый `APPROVED`, но `test-findings.md` нет или `TESTS_FAILED` |
| `reviewer` | `review/findings.md` существует, нет `APPROVED` |
| `dev` | `spec.md` существует, `review/findings.md` нет |
| `architect` | `task.md` существует, `spec.md` нет |
| `tracker` | `.agent/runs/<task-id>/` не существует (только ветка или вообще ничего) |

Пройденные фазы — все фазы левее текущей в цепочке `tracker → architect → dev → reviewer → qa_gate → mr → done`.

---

## Step 3: Рендер диаграммы

Выведи пользователю в блоке ```` ```mermaid ```` встроенный шаблон пайплайна (ниже), добавив в конец (после строк `class ...`) подсветку:

- Текущая фаза:
  ```text
  style <Node> fill:#ffe082,stroke:#f57f17,stroke-width:4px
  ```
- Каждая пройденная фаза:
  ```text
  style <Node> fill:#c8e6c9,stroke:#2e7d32,stroke-width:3px
  ```

Шаблон диаграммы (источник истины для чат-вывода; каноническая диаграмма документации — `docs/08-ai-agent-pipeline.drawio`, рендер `docs/08-ai-agent-pipeline.svg`):

```mermaid
%%{init: {'flowchart': {'curve': 'basis', 'padding': 20}}}%%
flowchart TD
    Entry(["/skill:*"])
    Entry --> Tracker

    Tracker["Tracker"]
    Tracker --> Worktree

    Worktree["git worktree<br/>.worktrees/{id}"]
    Worktree -.-> libs["libs"]
    Worktree -.-> best["best-pract"]
    Worktree -.-> code["codebase"]

    libs --> Architect
    best --> Architect
    code --> Architect

    Architect["Architect<br/><font color='#c62828'>⚠ plan mode required</font>"] <-.->|<i>прорабатывают архитектуру</i>| Human([Human])

    Architect --> Plan["PLAN.md"]
    Plan --> Approve{"auto / human<br/><i>approve?</i>"}
    Approve -.->|<font color='#c62828'>revise</font>| Plan
    Approve -->|<font color='#2e7d32'>approved</font>| Dev

    JiraCon["Jira / Confluence"] -.->|<i>spec context</i>| Architect
    Figma["Figma"] -.->|<i>design tokens</i>| Dev

    Dev --> SelfRev["Self-review<br/><i>adversarial audit diff</i>"]

    SelfRev --> Contract{"API contract<br/>backend ↔ frontend"}
    Contract -.->|<font color='#c62828'>расхождение</font>| Dev
    Contract -->|<font color='#2e7d32'>ok</font>| Reviewer

    Reviewer["Reviewer"] -->|<i>1-й проход & адаптивно к диффу</i>| Approved{APPROVED?}
    Reviewer -.->|<i>security-sensitive diff</i>| SecRev["security-reviewer"]
    SecRev --> Approved
    Approved -.->|<font color='#c62828'>нет</font>| Dev
    Approved -.->|<font color='#2e7d32'>да</font>| QA_Gate

    QA_Gate["QA Gate"] -->|<i>опционально · --qa</i>| MR

    MR["PR → GitHub"] --> KC["Knowledge Capture<br/><i>уроки → rules / skills / docs</i>"]
    KC --> Done([Done])

    noteBottom["re-review — один агент (шард при LARGE) · цикл до 3 итераций"]
    MR ~~~ noteBottom
    noteTrace["agent_state.py — trace.jsonl на границах фаз · correlation ID"]
    KC ~~~ noteTrace

    classDef entry fill:#f5f5f5,stroke:#9e9e9e,stroke-width:1px,color:#424242
    classDef tracker fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#1565c0
    classDef worktree fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,stroke-dasharray:5 5,color:#2e7d32
    classDef research fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px,color:#6a1b9a
    classDef human fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px,color:#6a1b9a
    classDef dev fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#2e7d32
    classDef review fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,color:#ef6c00
    classDef qa fill:#fffde7,stroke:#f9a825,stroke-width:2px,stroke-dasharray:5 5,color:#ef6c00
    classDef ship fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#c62828
    classDef note fill:none,stroke:none,color:#616161

    class Entry entry
    class Tracker tracker
    class Worktree worktree
    class libs,best,code research
    class Architect human
    class Human human
    class Dev dev
    class Plan dev
    class Approve review
    class SelfRev dev
    class Contract review
    class Reviewer review
    class SecRev review
    class Approved review
    class QA_Gate qa
    class MR ship
    class KC ship
    class Done ship
    class JiraCon research
    class Figma research
    class noteBottom note
    class noteTrace note
```

Имена узлов: `Tracker`, `Worktree`, `Architect`, `Dev`, `Reviewer`, `Approved`, `QA_Gate`, `MR`, `Done`. Маппинг фазы на узел: `tracker` → `Tracker`, `architect` → `Architect`, `dev` → `Dev`, `reviewer` → `Reviewer`, `qa_gate` → `QA_Gate`, `mr` → `MR`, `done` → `Done`. Узел `Worktree` подсвечивай как пройденный, если существует `.worktrees/<task-id>/` или ветка `feature|bugfix/<task-id>`.

Не перерисовывай диаграмму от себя — используй шаблон выше как источник истины, только добавляй `style`-строки.

---

## Step 4: Отчёт и следующее действие

Кратко, на русском:

- **Задача:** `<task-id>` · ветка `feature/<task-id>` (если есть)
- **Текущая фаза:** `<phase>` — одно предложение, что там происходит
- **Артефакты:** список из поля `artifacts`
- **Открытые замечания:** `findings.open` из state JSON и `[H-xxx]` из findings.md (если есть)
- **Следующий шаг:** одна конкретная команда, например:
  - `tracker` → `/skill:implement "<описание>"` или завести GitHub Issue
  - `architect` → ждать одобрения spec, затем продолжить `/skill:implement <task-id>`
  - `dev` → дождаться developer'ов или `/skill:implement <task-id>` продолжить
  - `reviewer` → developer правит findings, затем `/skill:review`
  - `qa_gate` → `/skill:qa-gate <task-id>`
  - `mr` → `/skill:ship` или review PR на GitHub
  - `done` → задача закрыта; `/skill:context-sync`

---

## Правила

- **Read-only:** не редактируй файлы, не запускай субагентов, тесты и `make`.
- Не двигай GitHub Project board и не комментируй PR.
- Диаграмма для чат-вывода всегда строится из встроенного шаблона (Step 3); каноническая документационная версия — `docs/08-ai-agent-pipeline.drawio` (генератор `scripts/docs/gen_diagrams.py`).
- Если `.agent/runs/<task-id>/` нет и ветки нет — скажи прямо, что задача не заведена, и предложи `/skill:implement`.
