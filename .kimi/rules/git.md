---
description: Git workflow rules
paths:
  - ".git/"
  - ".github/"
---

# Git Workflow

## Branches

- `main` — stable, deployable code. Protected.
- `feature/<name>` — new features
- `bugfix/<name>` — bug fixes
- `hotfix/<name>` — urgent production fixes

## Workflow

1. Create branch from main: `git checkout -b feature/name origin/main`
2. Implement with tests
3. Push branch: `git push -u origin feature/name`
4. Create PR via `gh pr create`
5. After review & tests pass — merge to main

## Commit Messages

Format: `<type>: <description>`

Types:
- `feat:` — new feature
- `fix:` — bug fix
- `refactor:` — code change without new features
- `test:` — adding/fixing tests
- `docs:` — documentation
- `chore:` — maintenance (deps, config)

## Forbidden

- ❌ `git push --force` to main
- ❌ `git reset --hard` on shared branches
- ❌ Direct commits to main (only via PR)
- ❌ Commits without user permission
