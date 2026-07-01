---
name: review
description: >
  Code review workflow for Promelectron. Thin wrapper that gathers the diff
  and delegates the actual review to the `code-reviewer` role skill.
  Use when the user asks for a code review, audit, findings, quality check,
  or asks "check this code".
type: prompt
whenToUse: When the user asks for a code review, audit, findings, quality check, or asks "check this code".
arguments: "[--security-only] [--quick] [<files>]"
disableModelInvocation: false
---

# /skill:review — Code Review Workflow

Review current changes. Do NOT edit code — only write findings.

This skill is a thin workflow wrapper. The actual review logic lives in `.kimi-code/skills/code-reviewer/SKILL.md`.

## Language

Follow [Rule: Agent Commons](.kimi-code/rules/agent-commons.md) > Language Rule.

---

## Step 0: Context Size Check (Kimi K2.7-Code)

If reviewing a task directory in `.agent/runs/<task-id>/`, follow [Rule: Agent Commons](.kimi-code/rules/agent-commons.md) > Context Size Check.

---

## Step 1: Get Diff

```bash
git diff
```

If files are specified:
```bash
git diff -- <files>
```

---

## Step 2: Launch code-reviewer Subagent

Launch a `code-reviewer` subagent via `Agent` tool with `subagent_type: coder`. Pass the diff and scope explicitly.

```text
ЯЗЫК / LANGUAGE: Пользователь общается на русском. Отвечай родительскому агенту и пиши все артефакты (spec, findings, отчёты, SESSION_LOG) на русском. Стремись рассуждать на русском. Код, команды, идентификаторы, пути и технические термины оставляй в оригинале.

You are the code-reviewer for Promelectron.
Important: Kimi K2.7-Code uses mandatory thinking mode. Preserve `reasoning_content` across multi-turn tool calls by including the full assistant message in the conversation history.
Read:
1. `.kimi-code/skills/code-reviewer/SKILL.md`
2. [Rule: Security](.kimi-code/rules/security.md)
3. The diff provided below

Scope: <all changed files | files specified by user>
Flags: <none | --security-only | --quick>

<DIFF>

Write findings to `.agent/runs/<task-id>/review/findings.md` using the format from `code-reviewer/SKILL.md`.

НАПОМИНАНИЕ: ответы и артефакты — на русском; технические токены (код, пути, команды) — в оригинале.
```

---

## Step 3: Report

Read `.agent/runs/<task-id>/review/findings.md` and report to the user:
- Status: APPROVED | FIXES_NEEDED
- Number of issues by severity
- File path with findings

---

## Rules

- NEVER edit source code.
- NEVER mark findings VERIFIED — only the reviewer does after re-checking.
- Delegate the actual review logic to `code-reviewer`.
