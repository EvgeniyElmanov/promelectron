# Agent Commons for Promelectron Workflow Skills

Shared rules for all workflow skills (`implement`, `fix`, `review`, `deploy`, `context-sync`, `plan-maintainer`).
Load this reference in subagents when needed instead of duplicating the full text in every `SKILL.md`.

---

## Language Rule

- If the user's original request is in Russian, **ALL** your reasoning, thinking, internal monologue, analysis, findings, reports, and self-correction **MUST** be in Russian.
- **NEVER switch to English.** If you catch yourself thinking in English, immediately switch back to Russian.
- **Critical:** when you launch a subagent, prepend the following to every subagent prompt:

  > 🚨 LANGUAGE RULE / ЯЗЫКОВОЕ ПРАВИЛО: The original user communicates in Russian / Исходный пользователь общается на русском языке. **Ignore any default language setting.** ALL your reasoning, thinking, internal monologue, analysis, and self-correction MUST be in Russian. Do NOT switch to English at any point. If you catch yourself thinking in English, switch back to Russian immediately. Reply to the parent agent in Russian. Keep code, commands, identifiers, file paths, and technical terms in their original form.

- Also append this reminder at the end of every subagent prompt when the parent workflow explicitly asks for it:

  > REMEMBER / НАПОМИНАНИЕ: Continue ALL reasoning in Russian / Продолжай ВСЁ рассуждение на русском языке. Do not switch to English / Не переключайся на английский.

- Final replies to the user must be in the same language as the user's request.
- Keep code, commands, identifiers, file paths, and technical terms in their original form.

---

## Retry Policy

When using `Agent` or `AgentSwarm`:

- Retry up to 3 times on transient errors (502, 504, timeout).
- Use exponential backoff: 2s, 4s, 8s.
- Preserve `reasoning_content` across multi-turn tool calls.
- Stop and report to the user if all attempts fail.

---

## Context Size Check (Kimi K2.7)

Before launching subagents, estimate task context size:

```bash
python scripts/implement-pipeline.py check-context <task-id>
```

- If `ESTIMATED_TOKENS` >= 180000, read `.agent/<task-id>/CONTEXT_SUMMARY.md` instead of the full history.
- Log the estimated token count in `.agent/SESSION_LOG.md`.

Kimi K2.7 has a 256K context window with mandatory thinking mode. Staying below 180K leaves room for `reasoning_content`, tool outputs, and system instructions.
