# Stage Overview

> Generated — do not edit manually. Source: `docs/stages/*.yaml`

| Stage | Depends On | Primary Features | Summary |
|---|---|---|---|
| `ranking` | `shortlist` | `cv_system` | Score shortlist candidates with the six-feature ranking contract, assign the authoritative post-filter ranking fit, and select the ranked jobs eligible to proceed toward CV generation. |

## Stage Contracts

Each stage has a contract at `docs/stages/<stage_id>.yaml`:

```text
docs/stages/<stage_id>.yaml
```

For the machine-friendly index, see `docs/generated/stages_index.yaml`.
