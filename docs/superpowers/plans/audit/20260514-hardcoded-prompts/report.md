# Audit Report With Evidence

## Metadata

- Audit ID: `20260514-hardcoded-prompts`
- Status: `open`
- Severity: `medium`
- Owner: `antigravity`
- Created At: `2026-05-14T10:35:00Z`
- Updated At: `2026-05-14T10:35:00Z`
- Related Thread/Plan: `none`

## Scope

- Environment: `windows/python`
- Commit/Branch: `current`
- Affected Surface: `src/fitcv_cp/app.py`

## Findings

### Finding `1`: `Hardcoded LLM prompt in application code`

- Classification: `data-quality`
- Impact: `Prompt management and pipeline configuration drift`
- Expected Behavior: `All LLM prompts should be loaded from the central templates directory src/fitcv/prompts/templates/.`
- Actual Behavior: `A synonym triage prompt is hardcoded directly in src/fitcv_cp/app.py.`

## Evidence

For each finding, include links to raw artifacts:

- Logs/Text: `evidence/app_snippet.py`

Each evidence item should include:

- capture timestamp: 2026-05-14T10:35:00Z
- producing command/tool: Source inspection
- checksum (sha256) from `manifest.yaml`: 74c7b01800bad1206e38a22aef05f826a807c963d5c7d027c1d701539eba7130

## Reproduction

- Preconditions:
  - `Codebase access`
- Steps:
  1. `Open src/fitcv_cp/app.py`
  2. `Navigate to line 3136`
- Commands:

```powershell
# exact reproducible commands
Get-Content src/fitcv_cp/app.py | Select-Object -Skip 3135 -First 10
```

- Determinism notes: `Static code artifact`

## Root Cause And Boundary

- Failure boundary: `src/fitcv_cp/app.py prompt definition`
- Root cause summary: `The synonym triage prompt was not migrated to the centralized fitcv.prompts registry and template system.`

## Fix And Verification

- Fix summary: `Extracted synonym-triage prompt to src/fitcv/prompts/templates/synonym_triage_recommendation_v1.md, registered prompt id synonym_triage.recommendation.v1 in src/fitcv/prompts/registry.py, and refactored src/fitcv_cp/app.py to call render_prompt(...) with proposal_json and now_iso context.`
- Verification commands:

```powershell
pytest -q tests/test_prompts.py -k synonym_triage
pytest -q tests/test_fitcv_cp/test_app.py -k "synonym_triage"
python scripts/audit_check.py docs/superpowers/plans/audit/20260514-hardcoded-prompts
```

- Verification evidence links:
  - `command output: pytest -q tests/test_prompts.py -k synonym_triage (2 passed)`
  - `command output: pytest -q tests/test_fitcv_cp/test_app.py -k "synonym_triage" (1 passed)`
  - `command output: python scripts/audit_check.py docs/superpowers/plans/audit/20260514-hardcoded-prompts (AUDIT_CHECK_PASSED)`

## Risk And Disposition

- Residual risk: `Low. Prompt text now versioned in centralized registry/template flow; remaining risk is ordinary future drift if new inline prompts are introduced outside this patch boundary.`
- Disposition decision: `resolved`
- Follow-ups: `Run broader app test lane separately; unrelated current failures in synonym-overlay upload tests are outside this audit fingerprint.`

## Artifact Index

- Manifest: `manifest.yaml`
- Evidence root: `evidence/`
- Repro root: `repro/`

## Completion Checklist

- [x] qualifying trigger documented (or explicit bypass)
- [x] evidence bundle linked and hashed
- [x] deterministic repro steps included
- [x] expected vs actual included
- [x] verification evidence attached
- [x] final status recorded
