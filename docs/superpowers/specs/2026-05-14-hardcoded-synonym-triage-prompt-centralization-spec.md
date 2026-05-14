---
layer: change
artifact_type: spec
status: active
parent_thread: workstream-agentic-synonym-management.hardcoded-synonym-triage-prompt-centralization
targets:
  - src/fitcv/prompts/templates/synonym_triage_recommendation_v1.md
  - src/fitcv/prompts/registry.py
  - src/fitcv_cp/app.py
  - tests/test_prompts.py
  - tests/test_fitcv_cp/test_app.py
  - docs/superpowers/plans/audit/20260514-hardcoded-prompts/report.md
related_features:
  - trigger_run_management
related_stages: []
---

# Hardcoded Synonym Triage Prompt Centralization Spec

## Summary

Move synonym-triage recommendation prompt text from inline control-plane code into centralized FitCV prompt template/registry surface and preserve strict JSON output contract used by provider-response parsing.

## Design Constraints

- keep response keys contract unchanged:
  - `recommended_action`
  - `recommendation_confidence`
  - `recommendation_rationale`
  - `recommendation_risk_flags`
- keep provider wiring unchanged (responses/chat payload paths)
- no unrelated prompt migration in same patch

## Verification

- `pytest -q tests/test_prompts.py -k synonym_triage`
- `pytest -q tests/test_fitcv_cp/test_app.py -k "synonym_triage"`
- `python scripts/audit_check.py docs/superpowers/plans/audit/20260514-hardcoded-prompts`
