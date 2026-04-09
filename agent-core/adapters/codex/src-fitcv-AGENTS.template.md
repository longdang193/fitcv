# FitCV Pipeline Instructions

This directory owns the pipeline runtime.

## Editing Rules

- Preserve stage and artifact truth when changing pipeline behavior.
- Keep stage-aware changes aligned with `docs/stages/*.yaml` and relevant feature docs.
- Keep repo operating rules in `docs/operating_system/`, not in pipeline-facing docs or code comments.
- Update tests when changing stage flow, fit gating, artifacts, or validation behavior.
- Prefer explicit contracts over hidden pipeline coupling.
