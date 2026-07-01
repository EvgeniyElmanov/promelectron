# Agent Commons for Promelectron Workflow Skills

Shared rules for all workflow skills (`implement`, `fix`, `review`, `deploy`, `context-sync`, `plan-maintainer`).
Load this reference in subagents when needed instead of duplicating the full text in every `SKILL.md`.

---

## Language Rule / Языковое правило

> **Это единый источник истины о языке.** Все прочие скиллы, правила и `AGENTS.md`
> ссылаются сюда и не дублируют формулировку.

Когда пользователь пишет по-русски:

- **Финальные ответы, отчёты и артефакты — на русском.** Это относится к ответам
  пользователю и родительскому агенту, а также к содержимому `task.md`, `spec.md`,
  `findings.md`, `test-findings.md`, `SESSION_LOG.md`, комментариям к PR и сообщениям.
- **Внутреннее рассуждение (thinking).** Модель Kimi K2.7-Code работает с
  принудительным thinking mode, и язык внутреннего рассуждения промптом надёжно не
  управляется. Стремись рассуждать по-русски, но сбой языка *thinking* не считается
  ошибкой выполнения — критичен язык итоговых ответов и артефактов.
- **Как реально усилить русский в рассуждении:** формулируй ключевые части задания
  (роль, задача, критерии проверки) по-русски или билингвально с русским впереди.
  Одна английская строка-«заклинание» в англоязычном контексте не работает.
- **Код, команды, идентификаторы, пути к файлам и технические термины** всегда
  оставляй в оригинальном виде.

### Преамбула для субагентов / Subagent preamble

Запуская субагента при русскоязычном пользователе, добавь эту директиву в **начало
и в конец** его промпта (единая формулировка, не изобретай свою):

> ЯЗЫК / LANGUAGE: Пользователь общается на русском. Отвечай родительскому агенту и
> пиши все артефакты (spec, findings, отчёты, SESSION_LOG) на русском. Стремись
> рассуждать на русском. Код, команды, идентификаторы, пути и технические термины
> оставляй в оригинале.

---

## Retry Policy

When using `Agent` or `AgentSwarm`:

- Retry up to 3 times on transient errors (502, 504, timeout).
- Use exponential backoff: 2s, 4s, 8s.
- Preserve `reasoning_content` across multi-turn tool calls.
- Stop and report to the user if all attempts fail.

---

## Model & API constraints (Kimi K2.7-Code)

The pipeline targets the **Kimi K2.7-Code** model. Fixed API parameters (any other
value errors out): `thinking={"type":"enabled"}` (mandatory, cannot be disabled),
`temperature=1.0`, `top_p=0.95`, `n=1`, `presence_penalty=0.0`,
`frequency_penalty=0.0`; `tool_choice` may only be `"auto"` or `"none"`. You **must**
preserve `reasoning_content` from the assistant message across multi-step tool calls.

## Context Size Check (Kimi K2.7-Code)

Before launching subagents, estimate task context size:

```bash
python scripts/implement-pipeline.py check-context <task-id>
```

- If `ESTIMATED_TOKENS` >= 180000, read `.agent/runs/<task-id>/CONTEXT_SUMMARY.md` instead of the full history.
- Log the estimated token count in `.agent/SESSION_LOG.md`.

Kimi K2.7-Code has a 256K context window with mandatory thinking mode. Staying below 180K leaves room for `reasoning_content`, tool outputs, and system instructions.
