---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: enrich-refactor-drift-remediation
parent_thread: workstream-pipeline-efficiency-and-reuse.efficiency-reuse-exact-match-contract
parent_spec: docs/superpowers/specs/2026-05-18-14-45-enrich-refactor-drift-remediation-spec.md
targets:
  - src/fitcv/enrich.py
  - tests/test_enrich.py
related_features: []
related_stages: []
---

## Goal

Implement bounded refactor and drift-remediation changes in `src/fitcv/enrich.py` that preserve behavior while restoring SSOT and structural symmetry across normalization, projection, and persistence paths.

## Key Deliverables

### Deliverable 1: Shared projection SSOT

A single projection helper maps enriched payloads to storage schemas for both structured and run-scoped sinks, including all JSON companion fields.

### Deliverable 2: Missing mapping-suggestion persistence fixed

`domain_mapping_suggestions` and `role_family_mapping_suggestions` persist and roundtrip in both BigQuery and SQLite-backed paths where schema projection applies.

### Deliverable 3: Normalization policy symmetry

Normalization behavior is governed by one policy object reused by parse and structured-normalization paths instead of repeated ad hoc config lookups.

### Deliverable 4: SQLite operational parity

SQLite write flows use one shared connection setup policy for WAL/synchronous/busy_timeout behavior.

### Deliverable 5: Regression-safe verification evidence

Tests and checks demonstrate no contract regressions and show drift fixes with explicit evidence.

## Task/Wave Breakdown

### Task 1: Baseline, impact gating, and fixture capture

**Purpose:**
- lock baseline behavior and blast radius before edits

**Files:**
- Inspect: `src/fitcv/enrich.py`
- Inspect: `tests/test_enrich.py`
- Verify: `docs/superpowers/specs/2026-05-18-14-45-enrich-refactor-drift-remediation-spec.md`

**Preconditions:**
- spec approved for execution
- worktree ready and baseline tests green

**Steps:**
- [ ] Run `uv run pytest tests/test_enrich.py -q` and record baseline
- [ ] Identify target symbols to edit (`_map_to_structured_jobs_row`, `_map_to_run_structured_jobs_row`, `_STRUCTURED_JSON_LIST_FIELDS`, `_STAGING_SCHEMA_FIELDS`, `_RUN_SCHEMA_FIELDS`, `_apply_structured_normalization`, `parse_extraction_response`, SQLite write helpers)
- [ ] Run GitNexus impact checks for each edit target when tooling available (`gitnexus_impact` upstream)
- [ ] If any HIGH/CRITICAL risk surfaced, pause and reorder edits interface-first

**Verification:**
- [ ] baseline test output captured
- [ ] impact gate evidence captured (or documented tool unavailability)

**Exit Criteria:**
- baseline behavior and risk map known before code modification

### Task 2: Projection SSOT extraction and schema parity patch

**Purpose:**
- remove duplicated row projection logic and patch schema-field drift

**Files:**
- Inspect: `src/fitcv/enrich.py`
- Modify: `src/fitcv/enrich.py`
- Verify: `tests/test_enrich.py`

**Preconditions:**
- Task 1 complete

**Steps:**
- [ ] Introduce shared projector helper (e.g., `project_enriched_row`) parameterized by schema keys, JSON list fields, and optional injected fields
- [ ] Refactor `_map_to_structured_jobs_row` and `_map_to_run_structured_jobs_row` to call shared projector only
- [ ] Extend schema constants to include JSON persistence columns for `domain_mapping_suggestions` and `role_family_mapping_suggestions`
- [ ] Ensure merge column lists and staging/run schema fields remain internally consistent
- [ ] Add/adjust tests proving projected payload includes all expected JSON companion fields

**Verification:**
- [ ] `uv run pytest tests/test_enrich.py -q`
- [ ] targeted assertions for mapper output include domain/role mapping suggestion JSON fields

**Exit Criteria:**
- one projection implementation path used by both storage mappers
- missing mapping-suggestion persistence drift resolved

### Task 3: NormalizationPolicy extraction (structural symmetry)

**Purpose:**
- centralize normalization config and eliminate repeated transform logic drift

**Files:**
- Inspect: `src/fitcv/enrich.py`
- Modify: `src/fitcv/enrich.py`
- Verify: `tests/test_enrich.py`

**Preconditions:**
- Task 2 complete

**Steps:**
- [ ] Introduce `NormalizationPolicy` data object containing synonyms, enum sets, alias maps, and role taxonomy hints
- [ ] Refactor normalization helpers to accept policy object instead of repeated raw config extraction
- [ ] Ensure parse path and structured-output path share same policy instance per operation scope
- [ ] Add regression tests comparing parse and structured paths for equivalent canonical outputs on same fixture

**Verification:**
- [ ] `uv run pytest tests/test_enrich.py -q`
- [ ] focused tests for enum coercion, skill canonicalization, and mapping suggestion generation parity

**Exit Criteria:**
- normalization rules have one operational source of truth

### Task 4: SQLite connection symmetry and parser warning telemetry

**Purpose:**
- align backend operational behavior and improve parse observability without behavior break

**Files:**
- Inspect: `src/fitcv/enrich.py`
- Modify: `src/fitcv/enrich.py`
- Verify: `tests/test_enrich.py`

**Preconditions:**
- Task 3 complete

**Steps:**
- [ ] Extract shared SQLite connection setup helper and use it in both `load_structured_jobs` and `load_run_structured_jobs`
- [ ] Extend `parse_extraction_response` to append tagged warning entries for coercion drops/invalids while preserving fallback non-throw contract
- [ ] Add tests for warning emission on invalid enum/non-list/invalid confidence cases
- [ ] Confirm no caller behavior regressions in merge/enrich paths

**Verification:**
- [ ] `uv run pytest tests/test_enrich.py -q`
- [ ] assertions for `errors` warning contents and non-throw behavior

**Exit Criteria:**
- SQLite path policy consistent across write flows
- parse warning channel improved with backward-safe semantics

### Task 5: Final verification, type checks, and scope guard

**Purpose:**
- prove completion and control blast radius before handoff

**Files:**
- Inspect: `src/fitcv/enrich.py`
- Inspect: `tests/test_enrich.py`
- Verify: `docs/superpowers/specs/2026-05-18-14-45-enrich-refactor-drift-remediation-spec.md`

**Preconditions:**
- Tasks 1-4 complete

**Steps:**
- [ ] Run final targeted tests for enrich module
- [ ] Run type checks for source package
- [ ] Run GitNexus changed-scope check when tooling available (`gitnexus_detect_changes`)
- [ ] Prepare concise implementation evidence summary mapped to spec acceptance criteria

**Verification:**
- [ ] `uv run pytest tests/test_enrich.py -q`
- [ ] `uvx mypy src --show-error-codes`
- [ ] `python scripts/hooks/run_validator.py --fast` (expect known unrelated baseline failure unless separately fixed)

**Exit Criteria:**
- evidence demonstrates acceptance criteria satisfied
- residual risks and known unrelated blockers documented

## Verification

- `uv run pytest tests/test_enrich.py -q`
- `uvx mypy src --show-error-codes`
- `python scripts/hooks/run_validator.py --fast`
- GitNexus checks when available:
  - `gitnexus_impact({target: <symbol>, direction: "upstream"})`
  - `gitnexus_detect_changes()`

## Completion Criteria

A plan item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>

## Triage

Layer: change  
Feature type: MODIFY  
Summary: Implement SSOT refactor and drift-remediation for enrichment projection, normalization, and persistence contracts.  
Reasoning: bounded implementation from approved detailed spec; no intent/governance redesign.  
Invariants:
- no external enrichment behavior regression
- payload roundtrip fidelity is improved or unchanged, never reduced
Dependencies:
- `docs/superpowers/specs/2026-05-18-14-45-enrich-refactor-drift-remediation-spec.md`
- `src/fitcv/enrich.py`
- `tests/test_enrich.py`
Affected stages:
- none
Affected features:
- none
Primary lens: cross-cutting
Affected docs:
- feature_source: none
- feature_yaml: none
- feature_lineage: none
- feature_history: none
- stage_source: none
- stage_contract: none
- feature_docs:
  - none
- cross_cutting_docs:
  - docs/superpowers/specs/2026-05-18-14-45-enrich-refactor-drift-remediation-spec.md
  - docs/superpowers/plans/2026-05-18-15-05-enrich-refactor-drift-remediation-plan.md
- readme: none
- generated:
  - docs/generated/planning_lineage.yaml
Generated refresh required: yes
Capability IDs:
- none
Invariant IDs:
- none
Spec needed: no
Plan needed: yes
