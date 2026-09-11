# `.agents/` — конфигурация агентов, общая для всех инструментов

Репозиторий ведут несколько CLI-агентов одновременно: Claude Code, Kimi Code, дальше Gemini.
Здесь лежит то, что у них **общее**: знание о проекте, роли и сценарии работы. У каждого
инструмента остаётся только привязка — тонкая, механическая, без содержания.

Причина простая: до этого одно и то же знание было записано дважды и уже разошлось.
`implement` — 274 строки у Claude против 673 у Kimi. `architect` существовал в трёх экземплярах.
Роли (`backend-dev`, `code-reviewer`, `devops`…) — субагентами у Claude и скиллами у Kimi,
разной длины. Третий агент превратил бы расхождение в правило.

---

## Что здесь

```
.agents/
├── skills/         сценарии работы: implement, ship, qa, board, sessions, backlog-*, …
├── agents/         кто за что отвечает: architect, backend-dev, code-reviewer, devops, …
└── conventions/    как здесь пишут код: api, models, testing, integrations, infra, …
```

| Каталог | Что внутри | Кто читает |
|---|---|---|
| `skills/` | `<имя>/SKILL.md` в формате Agent Skills | Claude — симлинком, Kimi — своей обёрткой |
| `agents/` | `<имя>.md` — определение роли без привязки к инструменту | субагенты Claude, ролевые скиллы Kimi |
| `conventions/` | `<тема>.md` с `paths:` в шапке — знание о коде | Claude — симлинком в `.claude/rules/` |

---

## Как подключено

**Claude Code — симлинками.** Документация это разрешает явно:

> A `<skill-name>` entry in the enterprise, personal, or project locations can be a symlink to a
> directory elsewhere on disk. Claude Code follows the symlink and reads `SKILL.md` from the
> target directory.

```
.claude/skills/<имя>  →  ../../.agents/skills/<имя>
.claude/rules/<тема>.md → ../../.agents/conventions/<тема>.md
```

Симлинки лежат в git как симлинки (mode `120000`) и разворачиваются при клоне.
⚠️ На Windows нужен режим разработчика или `git config core.symlinks true`.

**Субагенты Claude — не симлинками, а указателем.** `.claude/agents/<имя>.md` остаётся
настоящим файлом: у него Claude-специфичная шапка (`model`, `memory`, `skills`, `allowedTools`),
а тело первой же строкой отправляет читать `.agents/agents/<имя>.md`. Симлинки для субагентов
в документации **не заявлены**, а тихий отказ сломал бы делегирование в `/implement` незаметно —
поэтому здесь выбран механизм, который работает гарантированно.

**Kimi Code — тонкими обёртками-указателями, по модели субагентов Claude.** Симлинк
невозможен: Kimi-скиллу нужен собственный frontmatter (`type: prompt`, `whenToUse`,
`arguments`). Поэтому `.kimi-code/skills/<имя>/SKILL.md` — настоящий файл: Kimi-шапка,
первая строка тела отправляет читать общий файл (`.agents/skills/<имя>/SKILL.md` для
команд, `.agents/agents/<имя>.md` для ролей), а ниже — блок «Kimi-специфика» (retry
policy, trace-события, маппинг `subagent_type`, преамбулы субагентов, `/skill:`-вызовы).
Мигрированы: `architect`, `board`, `deploy`, `implement`, `qa`, `sessions`, `ship`;
остальные скиллы `.kimi-code/skills/` мигрируются по той же модели отдельными задачами.

---

## Правила

1. **Правится здесь, а не в копиях.** Файл под `.claude/` или `.kimi-code/` — это симлинк
   или указатель. Если правка ушла в копию, через сессию агенты будут работать по разным правилам.
2. **Инструменто-специфичное сюда не попадает.** `model`, `allowedTools`, формат шапки Kimi —
   всё это остаётся у инструмента. Здесь только то, что верно для любого агента.
3. **Новый скилл заводится здесь**, а в `.claude/skills/` появляется симлинк:
   ```bash
   mkdir -p .agents/skills/<имя> && $EDITOR .agents/skills/<имя>/SKILL.md
   ln -s ../../.agents/skills/<имя> .claude/skills/<имя>
   ```
   Скиллы регистрируются **на старте сессии** — новый увидит следующая, не текущая.
4. **`paths:` в конвенциях должны совпадать с реальной раскладкой.** Здесь код в
   `backend/src/app/`, а не в `backend/app/`. Четыре правила были написаны под несуществующий
   путь и не загружались вообще. Проверка — в `CLAUDE.md`.

Общие правила проекта и инварианты — `AGENTS.md` в корне.
Пульт запуска и замки — `ai-launcher/CONVENTIONS.md`.
