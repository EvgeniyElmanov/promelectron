# Task Directory

Each active task gets its own folder: `.agent/tasks/<task-id>/`

## Files

| File | Purpose |
|------|---------|
| `task.md` | What to do, why, acceptance criteria |
| `spec.md` | Architecture decisions, tech stack, API design |
| `progress.md` | Session notes, blockers, decisions made |
| `review.md` | Code review findings (created by reviewer agent) |

## Status Flow

```
[planning] → [ready] → [in-progress] → [review] → [done]
                ↑__________[blocked]_____________|
```

Update `progress.md` after every session.
