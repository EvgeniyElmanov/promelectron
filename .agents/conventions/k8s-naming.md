---
description: Kubernetes resource naming conventions
paths:
  - "infra/helm/templates/**"
---

# Kubernetes Naming Conventions

- CronJobs: `promelectron-cj-<name>` (e.g. `promelectron-cj-sync-onec`)
- Jobs (one-off): `promelectron-job-<name>` (e.g. `promelectron-job-migrate`)
- Deployments: `promelectron-<component>` (e.g. `promelectron-api`, `promelectron-worker`)
- Services/ConfigMaps/Secrets follow the same `promelectron-<component>` pattern
