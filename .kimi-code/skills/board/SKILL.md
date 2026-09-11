---
name: board
description: >
  Показать пульт запуска ai-launcher/BOARD.md и, по аргументу refresh, привести его
  в соответствие с живым состоянием — открытые issue, ветки, PR, замки, статусы.
  Борд — витрина открытых GitHub Issues, а не отдельный список.
type: prompt
whenToUse: Когда пользователь спрашивает «что у нас», «покажи борд», «что можно брать», или когда после закрытия PR борд нужно пересчитать.
arguments: "[refresh]"
disableModelInvocation: false
---

# /skill:board — пульт запуска

**Первым делом прочитай `.agents/skills/board/SKILL.md` — там тело сценария, общее для всех агентов проекта. Правится там, а не здесь.** Ниже — только Kimi-специфика.

## Kimi-специфика

- Язык: [Rule: Agent Commons](../../rules/agent-commons.md) > Language Rule (преамбула для субагентов — раздел Full subagent prompt block там же).
- Команды в общем файле названы нейтрально; у Kimi они вызываются как `/skill:<имя>` (например, `/skill:board refresh`).
