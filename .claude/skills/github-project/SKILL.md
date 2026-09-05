---
name: github-project
description: Move a task's card through the GitHub Project (v2) status column as the /implement pipeline progresses. Runtime-discovers the project, the Status field, and its option IDs via gh, caches them, and exposes the exact gh commands to transition status. Used by /implement, /architect, /ship.
when_to_use: Load whenever a pipeline command works on a task that came from a GitHub Issue and must reflect progress on the GitHub Project board (start → In Progress, PR opened → In Review, etc.).
user-invocable: false
---

# GitHub Project status movement

When a task originates from a **GitHub Issue** that sits on a **GitHub Project (v2)** board, the
pipeline moves its card through the status column as work progresses. This skill is the single
source of truth for *how* to do that with the `gh` CLI.

> **Scope rule (important):** the **agent code-review loop inside `/implement` does NOT move the
> status.** Only human-facing milestones move the card:
> `start work → In Progress` and `PR opened (ready for a human) → In Review`. The internal
> architect→dev→reviewer→qa iterations are invisible to the board. This is deliberate — the
> "In Review" column means *a human should look*, not *an agent is looking*.

## Prerequisites (check once, fail loudly)

1. `gh` must be installed and authenticated:
   ```bash
   gh auth status
   ```
2. The token needs the **`project`** scope (read **and** write). Read-only board needs
   `read:project`; moving cards needs `project`. If a `gh project …` call returns
   `missing required scopes [read:project]` (or `project`), STOP and tell the user to run, in
   their own shell (it is interactive — you cannot do it):
   ```
   gh auth refresh -s project
   ```
   Do not silently skip status updates without telling the user the board is out of sync.

If the task did **not** come from a GitHub Issue (free-text task), there is no card — skip every
status step silently.


## Запасной путь без scope: метки

Доска — витрина, а не единственный носитель состояния. Если `gh project …` отвечает
`missing required scopes`, **конвейер не останавливается**: ту же информацию несут метки,
которым хватает обычного доступа к репозиторию.

| Колонка доски | Метка-эквивалент |
|---|---|
| In Progress | `in-progress` |
| In Review | `in-review` |
| Todo | нет меток статуса |
| Done | issue закрыт |

```bash
gh issue edit <N> --repo AutonomaCo/promelectron --add-label in-progress
gh issue edit <N> --repo AutonomaCo/promelectron --remove-label in-progress --add-label in-review
```

Метка зоны (`backend` · `frontend` · `e2e` · `infra` · `docs` · `harness`) — это **замок**
пункта, из неё борд берёт, что занято. Полный порядок движения — `ai-launcher/CONVENTIONS.md` §8.

Скажи владельцу про `gh auth refresh -s project`, отметь на борде, что колонки не сверялись, и
работай дальше по меткам.

## Config cache

Discovery is **already done** and cached in `.claude/.github-project.json` (committed — it holds
opaque GitHub node IDs, no secrets). Read it instead of rediscovering.

Project: **`AutonomaCo/1`** — https://github.com/orgs/AutonomaCo/projects/1

### Columns of THIS board

`Backlog` → `Ready` → `In progress` → `In review` → `Done`. Note the lowercase second words —
`In progress`, not `In Progress`; an exact-name mismatch silently no-ops.

| Milestone | Column |
|---|---|
| заведён | `Backlog` |
| **промпт написан, замок свободен** | `Ready` — то же, что 🟢 с кнопкой на пульте |
| взят в работу | `In progress` |
| PR открыт | `In review` |
| смержен | `Done` |

`Ready` — единственная колонка, которую двигает не конвейер, а приоритизация: пункт попадает
туда, когда для него написан промпт в `ai-launcher/prompts/`.

### ⚠️ Два разных вида полей — и разные мутации

Это главная ловушка этой доски.

**Поля доски** — `Status`, `Size`, `Замок`. Пишутся обычным путём:

```bash
gh project item-edit --id <itemId> --project-id <projectId> \
  --field-id <fieldId> --single-select-option-id <optionId>
```

**Поля уровня issue** — `Priority`, `Start date`, `Target date`, `Effort`. Живут на самой issue
(видны и вне проекта) и через `updateProjectV2ItemFieldValue` **не пишутся**: GraphQL отвечает
`Issue field values cannot be updated using the updateProjectV2ItemFieldValue mutation`.
Им нужна своя мутация:

```bash
gh api graphql -f query='
mutation { updateIssueFieldValue(input:{
  issueId: "<issue node id>"
  issueField: { fieldId: "IFSS_kgDOAoI0Aw", singleSelectOptionId: "<optionId>" }
}) { clientMutationId } }'
```

Для даты вместо `singleSelectOptionId` идёт `dateValue: "2026-09-08"`. Node id issue берётся так:
`gh api graphql -f query='query{repository(owner:"AutonomaCo",name:"promelectron"){issue(number:N){id}}}' -q .data.repository.issue.id`

По той же причине **встроенный `Priority` нельзя переопределить** своими вариантами:
`updateProjectV2Field` отвечает `Only custom fields can be updated`. Поэтому используется его
родная шкала, а соответствие меткам репозитория такое:

| Priority на issue | Метка | Что значит |
|---|---|---|
| `Urgent` | `P0` | деньги, данные, доступ |
| `High` | `P1` | ломается молча |
| `Medium` | `P2` | когда освободятся руки |

### Виды доски

`Backlog` · `Priority board` · `Team items` · `Roadmap` (по `Start date` / `Target date`) ·
`My items` · `Замки`. Создать вид можно (`createProjectV2View`), а вот **группировку внутри вида
API не отдаёт** — `configuration` принимает только `visibleFieldIds`. Группировку по `Замок`
владелец ставит руками.

## Discovery (run when cache is absent)

The repo's issues already live on a board, so the most reliable anchor is an existing issue.
Pick any open issue number `<N>` (e.g. `gh issue list --limit 1 --json number`):

```bash
gh api graphql -f query='
  query($o:String!,$r:String!,$n:Int!){
    repository(owner:$o,name:$r){
      issue(number:$n){
        projectItems(first:10){ nodes{
          id
          project{ number title id owner{ __typename ... on Organization{login} ... on User{login} } }
          fieldValueByName(name:"Status"){ ... on ProjectV2ItemFieldSingleSelectValue{ name optionId } }
        }}
      }
    }
  }' -F o=AutonomaCo -F r=promelectron -F n=<N>
```

That yields the `projectId`, `projectNumber`, and `owner`. Then pull every Status option id:

```bash
gh project field-list <projectNumber> --owner <owner> --format json \
  | jq '.fields[] | select(.name=="Status") | {fieldId:.id, options:.options}'
```

Write the result into `.claude/.github-project.json`. Match the discovered column names to the
three transition milestones (`start`, `pr_opened`, `merged`) — fuzzy-match is fine (`In Progress`
/ `In progress` / `Doing`; `In Review` / `Review`; `Done` / `Closed`). If a milestone has no
matching column, leave it `null` and note it — that milestone simply won't move the card.

## Find a task's project item id

To move a specific issue's card you need its **item id** on the board:

```bash
gh api graphql -f query='
  query($o:String!,$r:String!,$n:Int!){
    repository(owner:$o,name:$r){ issue(number:$n){ projectItems(first:10){ nodes{
      id project{ number }
      fieldValueByName(name:"Status"){ ... on ProjectV2ItemFieldSingleSelectValue{ name } }
    }}}}
  }' -F o=AutonomaCo -F r=promelectron -F n=<ISSUE_N> \
  | jq -r --argjson pn <projectNumber> '.data.repository.issue.projectItems.nodes[] | select(.project.number==$pn) | .id'
```

If the issue is **not yet on the board** (no item), add it first:

```bash
gh project item-add <projectNumber> --owner <owner> --url https://github.com/AutonomaCo/promelectron/issues/<ISSUE_N>
```

## Set the status (the actual transition)

```bash
gh project item-edit \
  --id "<ITEM_ID>" \
  --project-id "<projectId>" \
  --field-id "<statusFieldId>" \
  --single-select-option-id "<option id for the target column>"
```

Helper to resolve the option id from the cache for a milestone:

```bash
# milestone = start | pr_opened | merged
col=$(jq -r '.transitions["<milestone>"]' .claude/.github-project.json)
opt=$(jq -r --arg c "$col" '.options[$c]' .claude/.github-project.json)
# then pass $opt as --single-select-option-id
```

Always read the card's **current** status before moving it: never move a card *backwards*
(e.g. don't push a `Done` card back to `In Progress` on a re-run) and skip the call if it is
already in the target column.

## Where the pipeline calls this

| Milestone (in `/implement`) | Transition | Notes |
|-----------------------------|-----------|-------|
| Task fetched, worktree created, dev about to start | `start` → **In Progress** | Only if the task is a GitHub Issue and not already past this column. |
| Architect spec / agent code-review / QA loops | **(no move)** | Internal agent work never touches the board. |
| PR created (ready for human review) | `pr_opened` → **In Review** | This is the *human* review signal. |
| PR merged | `merged` → **Done** | `/implement` does **not** merge, so it does not set Done by default — that is left to the human or a GitHub merge automation. `/ship` may set it if asked. |

## Rules

1. **Agent review ≠ board "In Review".** Never move the card during the internal review loop.
2. **GitHub Issue tasks only.** Free-text tasks have no card — skip silently.
3. **Idempotent.** Read current status; skip if already there; never regress a column.
4. **Fail loud on missing scope.** If `project` scope is absent, tell the user how to fix it and
   note the board was not updated — do not pretend it succeeded.
5. **Cache, don't hardcode.** All ids live in `.claude/.github-project.json`; re-discover if a
   call stops matching.
