# MCP-интеграции — Promelectron

Проект использует [Model Context Protocol (MCP)](https://modelcontextprotocol.io) для подключения внешних систем к агентскому пайплайну. Конфигурация находится в `.kimi-code/mcp.json`.

## Подключённые MCP-серверы

| Сервер | Назначение | Статус |
|--------|------------|--------|
| `playwright` | Браузерная автоматизация (E2E, smoke) | активен |
| `filesystem` | Чтение/запись файлов проекта | активен |
| `memory` | Память агента | активен |
| `sequential-thinking` | Многошаговое рассуждение | активен |
| `kubernetes` | Операции с K8s кластером | активен |
| `figma` | Чтение макетов и design tokens | **требует `FIGMA_ACCESS_TOKEN`** |
| `atlassian` | Jira issues + Confluence pages | **требует `ATLASSIAN_URL`, `ATLASSIAN_USERNAME`, `ATLASSIAN_API_TOKEN`** |

## Figma

### Токен

1. Открой [Figma Settings → Personal Access Tokens](https://www.figma.com/developers/api#access-tokens).
2. Создай новый токен с scope `file_content`.
3. Добавь в `.env` (локально) и в секреты CI/CD:
   ```bash
   FIGMA_ACCESS_TOKEN=figd_xxx
   ```

### File key

File key — это часть URL макета:
```
https://www.figma.com/design/FILE_KEY/...
```

### Доступные инструменты

- `get_file` — метаданные и дерево документа.
- `get_variables` — переменные (colors, spacing, typography tokens).
- `get_styles` — опубликованные стили.
- `get_components` — компоненты.
- `get_design_tokens` — агрегированный summary токенов.

### Использование в пайплайне

В `/skill:implement` Step 0.5: если в spec указан `figma_file_key`, агент через MCP забирает design tokens и применяет их при генерации frontend-кода.

## Atlassian (Jira + Confluence)

### Токен

1. Создай API token: https://id.atlassian.com/manage-profile/security/api-tokens
2. Добавь в `.env`:
   ```bash
   ATLASSIAN_URL=https://your-domain.atlassian.net
   ATLASSIAN_USERNAME=you@example.com
   ATLASSIAN_API_TOKEN=xxx
   ```

### Доступные инструменты

- `jira_get_issue` — получить issue по ключу (`PROJ-123`).
- `jira_search_issues` — поиск по JQL.
- `confluence_get_page` — получить страницу по ID.
- `confluence_search_pages` — поиск по CQL.

### Использование в пайплайне

В `/skill:spec` Step 0.5: если в `task.md` указан `jira_issue`, агент через MCP подтягивает summary и description в spec. Если есть `confluence_spec_url` — подтягивает страницу как дополнительный контекст.

## Безопасность

- Токены хранятся только в env vars и в секретах CI/CD. **Никогда не коммить токены в репозиторий.**
- `.kimi-code/mcp.json` использует подстановку `${VAR}` — значения подхватываются из окружения Kimi Code CLI.
- Логировать ответы MCP в `trace.jsonl` и `SESSION_LOG.md` можно, но **вычищай токены и PII** перед записью.
- API tokens дают доступ ко всем файлам/задачам, доступным пользователю. При компрометации — отозвать на странице управления токенами.

## Отладка

Проверить, что MCP-сервер стартует:

```bash
FIGMA_ACCESS_TOKEN=test python3 scripts/mcp_figma.py
# В другом терминале:
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | python3 scripts/mcp_figma.py
```

```bash
ATLASSIAN_URL=https://... ATLASSIAN_USERNAME=... ATLASSIAN_API_TOKEN=... python3 scripts/mcp_atlassian.py
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | python3 scripts/mcp_atlassian.py
```

## Troubleshooting

- **MCP server failed to start** — проверь, что env vars выставлены в сессии Kimi Code CLI (не только в `.env`).
- **Figma API 403** — токен не имеет доступа к файлу, или файл приватный для другой команды.
- **Atlassian 401** — неверный API token или email; убедись, что `ATLASSIAN_USERNAME` — это email, а не display name.
