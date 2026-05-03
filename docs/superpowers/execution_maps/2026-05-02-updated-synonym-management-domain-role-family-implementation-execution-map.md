---
layer: change
artifact_type: execution_map
status: proposed
parent_workstream: workstream-agentic-synonym-management
map_type: implementation_execution
threads:
  - workstream-agentic-synonym-management.agentic-synonym-proposal-engine
specs:
  - docs/superpowers/specs/2026-05-02-updated-synonym-management-domain-role-family-spec.md
---

# 2026-05-02 Updated Synonym Management (Domain + Role Family) Implementation Execution Map

## Metadata
- Date: 2026-05-02
- Source spec: `docs/superpowers/specs/2026-05-02-updated-synonym-management-domain-role-family-spec.md`
- Primary objective: extend synonym-management lifecycle and ranking normalization to `domain` and `role_family` with low-risk staged rollout

## Execution Principles
1. Preserve skill-synonym behavior and contracts.
2. Land additive schema/logic first; enable new behavior behind safe defaults.
3. Verify each wave with targeted tests before continuing.
4. Keep run-level observability strong enough to explain ranking deltas.

## Wave Plan

## Wave 1: Data Model + Canonicalization Primitives
### Scope
- Add canonical maps and normalization helpers for:
  - `domain_alias_map`
  - `role_family_alias_map`
- Add optional adjacency maps:
  - `domain_neighbors`
  - `role_family_neighbors`
- Keep ranking behavior unchanged until Wave 3 wiring.

### File Ownership
- `src/fitcv/config.py`
  - extend config load/default/normalization for new maps
- `src/fitcv/ranking.py`
  - add helper functions for canonicalization + neighbor checks (not yet used in final score path)
- `tests/test_config.py`
  - defaults + normalization tests for new config keys
- `tests/test_pipeline.py` (if needed for config passthrough assertions)

### Deliverables
1. Config accepts and normalizes new map keys.
2. Helper functions are deterministic and unit-tested.
3. No ranking score behavior change yet.

### Verification Gate
- `pytest -q tests/test_config.py -k "domain_alias_map or role_family_alias_map or neighbors"`
- Existing ranking tests remain green.

---

## Wave 2: Mapping Suggestions + Proposal Lifecycle Parity
### Scope
- Generate mapping suggestions for `domain` and `role_family`.
- Persist/export new field-specific suggestion artifacts.
- Extend proposal generation and review queue to support field-tagged proposals.
- Suppress already-global exact mappings for both fields.

### File Ownership
- `src/fitcv/pipeline.py`
  - extend `_collect_mapping_suggestions` to emit `field` and include domain/role-family candidates
- `src/fitcv_cp/worker_job.py`
  - extend proposal payload builder for multi-field (`skill`, `domain`, `role_family`)
  - preserve existing proposal status/review history behavior
- `src/fitcv_cp/app.py`
  - review queue display + counters per field
  - export links for new suggestion artifacts
- `tests/test_fitcv_cp/test_worker_job.py`
  - proposal grouping, suppression, conflict handling for new fields
- `tests/test_fitcv_cp/test_app.py`
  - queue filtering/rendering + artifact endpoint tests

### Deliverables
1. `domain`/`role_family` suggestions appear in run artifacts.
2. Proposals are generated with conflict and suppression logic.
3. Already-global exact mappings do not appear in pending review queue.

### Verification Gate
- `pytest -q tests/test_fitcv_cp/test_worker_job.py -k "synonym_proposals and (domain or role_family or suppressed)"`
- `pytest -q tests/test_fitcv_cp/test_app.py -k "synonym_proposal and (domain or role_family or filtered)"`

---

## Wave 3: Ranking Integration + Diagnostics
### Scope
- Apply canonical maps in preference-fit computation.
- Add optional neighbor-based partial matching.
- Emit diagnostics for raw/canonical values and match type.

### File Ownership
- `src/fitcv/ranking.py`
  - integrate canonicalization into `compute_preference_fit_details`
  - add match-type outputs and neighbor-score application
- `src/fitcv/pipeline.py`
  - ensure export payload includes ranking diagnostics fields
- `tests/test_pipeline.py`
  - ranking ratio behavior tests with canonicalized/neighbor cases
- `tests/test_cv_generator.py` or related tests only if impacted by changed diagnostics payloads

### Deliverables
1. Preference-fit uses canonicalized `domain` and `role_family`.
2. Neighbor scoring is configurable and deterministic.
3. Run artifacts explain ratio outcomes via match diagnostics.

### Verification Gate
- `pytest -q tests/test_pipeline.py -k "preference_fit and (canonical or domain or role_family or neighbor)"`
- `pytest -q tests/test_pipeline.py -k "export_results and preference_fit_components"`

---

## Wave 4: Rollout Controls + Safety Checks
### Scope
- Introduce staged rollout flags:
  - shadow/propose-only
  - apply-to-run-enabled
  - promote-global-enabled
- Add summary metrics for monitoring drift and operator load.

### File Ownership
- `src/fitcv_cp/settings_schema.py`
  - add control-plane toggles (if absent)
- `src/fitcv_cp/app.py`
  - expose rollout status in run detail
- `src/fitcv_cp/worker_job.py`
  - enforce mode behavior in proposal/apply paths
- `tests/test_fitcv_cp/test_settings_schema.py`
  - schema defaults and constraints

### Deliverables
1. Safe progressive enablement.
2. Clear run-level indicators of active mode.
3. No accidental auto-promotion.

### Verification Gate
- `pytest -q tests/test_fitcv_cp/test_settings_schema.py -k "synonym or alias map or rollout"`
- `pytest -q tests/test_fitcv_cp/test_app.py -k "settings and synonym"`

---

## Cross-Wave Validation Checklist
1. Skill-synonym proposal flow unchanged for existing cases.
2. No regression in artifact bundle generation and manifest states.
3. Proposal suppression works for pre-existing run/global map entries.
4. Ranking deltas are explainable from diagnostics fields.

## Suggested Command Sequence
1. `pytest -q tests/test_config.py`
2. `pytest -q tests/test_fitcv_cp/test_worker_job.py`
3. `pytest -q tests/test_fitcv_cp/test_app.py`
4. `pytest -q tests/test_pipeline.py -k "preference_fit or mapping_suggestions or synonym"`
5. `python scripts/validate_repo_contracts.py --fast`

## Risk Controls
1. Keep neighbor scoring off by default until shadow results are reviewed.
2. Cap suggestion/proposal payload sizes to avoid oversized artifacts.
3. Preserve backward-compatible JSON schemas with additive fields only.

## Rollback Strategy
1. Disable alias-map application flags while leaving artifacts/proposals visible.
2. Revert ranking to exact canonical only (or current raw-normalized behavior) via config toggle.
3. Preserve review data; do not delete generated proposals on rollback.

## Done Criteria
1. `domain` and `role_family` run through full suggestion-to-promotion lifecycle.
2. Preference-fit ratios are canonicalization-aware and diagnostically explainable.
3. Existing skill synonym behavior is preserved and regression-tested.
4. Rollout controls and safety gates are verified in tests.
