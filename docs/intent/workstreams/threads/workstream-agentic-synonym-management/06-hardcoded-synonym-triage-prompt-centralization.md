---
thread_id: workstream-agentic-synonym-management.hardcoded-synonym-triage-prompt-centralization
status: active
---

# hardcoded-synonym-triage-prompt-centralization

## Goal

Centralize synonym-triage recommendation prompt into shared prompt template + registry, remove inline prompt string from control-plane call path, and preserve strict JSON response contract.

## Why Now

Audit `20260514-hardcoded-prompts` confirmed hardcoded prompt drift risk in control-plane path.

## Dependencies

- workstream-agentic-synonym-management.agentic-synonym-review-queue-and-approval

## Shared Surfaces

- `src/fitcv/prompts/templates/`
- `src/fitcv/prompts/registry.py`
- `src/fitcv_cp/app.py`
- `docs/superpowers/plans/audit/20260514-hardcoded-prompts/`

