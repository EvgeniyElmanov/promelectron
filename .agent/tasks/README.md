# Task Directory

Active tasks are stored as flat markdown files: `.agent/tasks/TASK-XXX-descriptive-name.md`

## Naming Convention

```
TASK_YOOKASSA_PLAN.md
TASK-042-fix-celery-worker.md
```

## File Contents

Each task file should include:
- **Status:** planning / ready / in-progress / review / done / blocked
- **Assignee:** backend-dev / frontend-dev / devops / e2e-tester / etc.
- **Description:** What to do, why, acceptance criteria
- **Dependencies:** Blockers or other tasks
- **Progress notes:** Updated after each session

## Status Flow

```
[planning] → [ready] → [in-progress] → [review] → [done]
                ↑__________[blocked]_____________|
```

Update the task file after every session.
