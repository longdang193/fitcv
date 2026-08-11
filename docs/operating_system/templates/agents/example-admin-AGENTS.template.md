# Admin Surface Instructions

This directory owns operator-facing or admin-facing orchestration behavior.

## Editing Rules

- Keep operator-facing behavior aligned with the underlying contracts and artifacts.
- Update routes, templates, and serialization together when an operator workflow changes.
- Preserve clear distinctions between private operating workflow and product-facing UX.
- Keep governance and publication guidance in `docs/operating_system/`; keep
  machine-enforced policy in `repo_config/`, not UI docs.
