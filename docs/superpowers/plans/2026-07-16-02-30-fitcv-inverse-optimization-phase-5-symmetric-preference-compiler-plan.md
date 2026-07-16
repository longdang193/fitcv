---
layer: change
artifact_type: plan
status: completed
completed_at: 2026-07-16T03:18:34+02:00
change_id: 2026-07-16-fitcv-inverse-optimization-phase-5-symmetric-preference-compiler
verification:
  - python -m pytest tests/test_decision_feedback.py -q
  - python -m pytest tests/test_config.py tests/test_decision_feedback.py -q
  - python -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_worker_job.py -q -k "decision_feedback or admin_route_manifest"
  - python -m pytest tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py -q
  - python -m pytest tests/test_ranking.py tests/test_ranking_contract.py tests/test_ai_score.py -q
  - python -m ruff check src/fitcv/decision_feedback.py tests/test_decision_feedback.py
  - uvx mypy src/fitcv/decision_feedback.py --show-error-codes --follow-imports=skip
  - python tools/docs/generate_architecture_metadata.py --check
  - python scripts/validate_planning_lifecycle.py
  - python scripts/hooks/run_validator.py --fast
  - python scripts/validate_repo_contracts.py --fast
  - git diff --check
outcome:
  summary: Completed Phase 5 deterministic ordinal preference compilation with one policy SSOT, provenance-preserving watermark replay, exhaustive symmetric pair compilation, episode-bounded evidence weights, canonical fingerprints, and no persistence, solver, activation, or ranking effect.
template_id: implementation-plan
name: fitcv-inverse-optimization-phase-5-symmetric-preference-compiler-implementation
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-stage-authority-contract
parent_spec: docs/superpowers/specs/2026-07-16-02-18-fitcv-inverse-optimization-phase-5-symmetric-preference-compiler-spec.md
targets:
  - docs/superpowers/specs/2026-07-16-02-18-fitcv-inverse-optimization-phase-5-symmetric-preference-compiler-spec.md
  - config/policy/decision_learning.yaml
  - src/fitcv/config.py
  - src/fitcv/decision_feedback.py
  - docs/architecture.md
  - docs/configuration.md
  - docs/pipeline.md
  - docs/stages/ranking.source.yaml
  - docs/stages/ranking.yaml
  - docs/features/cv_system/feature.source.yaml
  - docs/features/cv_system/cv_system.yaml
  - docs/features/cv_system/history.md
  - docs/features/cv_system/lineage.generated.yaml
  - docs/generated/architecture_dag.yaml
  - docs/generated/capability_lineage.yaml
  - docs/generated/planning_lineage.yaml
  - tests/test_config.py
  - tests/test_decision_feedback.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - tests/test_fitcv_cp/test_store.py
  - tests/test_pipeline.py
  - tests/test_pipeline_stage_resume_parity.py
  - tests/test_ranking.py
  - tests/test_ranking_contract.py
  - tests/test_ai_score.py
related_features:
  - cv_system
related_stages:
  - ranking
---

# FitCV inverse optimization Phase 5 symmetric preference compiler implementation plan

## Goal

Implement one pure, deterministic compiler from Phase 4 ordinal rating events to
versioned weighted preference edges:

```text
one compatible decision episode
+ complete events through event_watermark
-> one provenance-preserving effective-state reducer
-> every unordered pair once
-> omit unrated, equal, and below-gap pairs
-> orient qualifying pairs higher -> lower
-> apply versioned gap weight
-> apply one episode-wide budget scale
-> canonical edge set, diagnostics, and fingerprints
```

Execution boundaries:

- use Python standard library and existing `build_contract_fingerprint(...)` only
- extend existing `decision_feedback.py`; add no service, graph layer, or new module
- extend existing `decision_learning.yaml`; add no second policy file
- preserve append-only SQLite ledger as sole persisted rating truth
- preserve existing UI-visible `reduce_rating_events(...)` output
- add no DB table, route, worker, pipeline stage, settings control, cache, or migration
- add no NumPy, CVXPY, solver, learned vector, evaluation, activation, or ranking effect
- leave unrelated `.tmp-tests/` content untouched
- write failing tests before each production behavior change

## Key Deliverables

### One exact compiler-policy SSOT

Extend `decision_learning_policy` with exact compiler version, minimum gap,
strictly increasing gap weights, and positive episode budget. Loader continues
to reject env/settings shadows and returns deterministic normalized policy
fingerprint.

### One canonical effective-state reducer

Add provenance-preserving effective states and route the existing simple rating
projection through the same latest-event algorithm. Watermark replay uses SQLite
`event_sequence` only.

### One shared candidate-set identity helper

Extract Phase 4 candidate-set identity construction from inline source-builder
code. Reuse it for source creation, persisted-source validation, and compiler
compatibility. No count-only or URL identity fallback.

### One pure symmetric compiler

Add frozen edge, diagnostic, and result records plus one
`compile_preference_edges(...)` function using standard-library unordered pair
enumeration, deterministic ordering, episode budgeting, source event IDs, and
canonical fingerprints.

### One source-derived lifecycle handoff

Update human-owned feature/stage/docs sources, regenerate managed outputs, prove
Phase 3 and Phase 4 regressions, and close the plan with exact evidence.

## Task/Wave Breakdown

### Task 1: Refresh impact map and add failing acceptance tests

**Purpose:** freeze execution scope and make Phase 5 behavior executable before production edits.

**Files:**

- Inspect: `docs/superpowers/specs/2026-07-16-02-18-fitcv-inverse-optimization-phase-5-symmetric-preference-compiler-spec.md`
- Inspect: `src/fitcv/decision_feedback.py`
- Inspect: `src/fitcv/config.py`
- Inspect: `src/fitcv_cp/app.py`
- Modify: `tests/test_config.py`
- Modify: `tests/test_decision_feedback.py`
- Verify: existing Phase 3 and Phase 4 suites

**Preconditions:**

- Phase 4 commit `55875f96` is present
- Phase 5 spec is current source of truth
- GitNexus index is stale at `1722d631` and lacks Phase 4 symbols

**Steps:**

- [x] Step 1: Run `gitnexus analyze`; fall back to `npx gitnexus analyze` only if command is unavailable.
- [x] Step 2: Run upstream impact for `validate_decision_learning_policy`, `reduce_rating_events`, and `build_decision_feedback_source` after refresh.
- [x] Step 3: Report direct callers, affected processes, and risk; stop for confirmation if refreshed impact is HIGH or CRITICAL.
- [x] Step 4: Record source-first caller map when GitNexus remains unavailable or degraded.
- [x] Step 5: Extend policy test fixtures with exact `preference_compiler` block.
- [x] Step 6: Add failing policy tests for missing/extra keys, invalid minimum gap, nonfinite/nonpositive/nonmonotonic weights, invalid budget, settings/env shadow absence, and alternate valid compiler values.
- [x] Step 6a: Add failing identity test proving rating-label changes alter full policy, compiler-input, and edge-set fingerprints without altering compiler-block fingerprint.
- [x] Step 7: Add failing provenance-reducer tests for no event, set, repeated set, change, clear, shuffled input, duplicate event ID/sequence, and watermark replay.
- [x] Step 8: Add exhaustive table-driven tests for all 36 pairs in `{unrated,1,2,3,4,5}²`.
- [x] Step 9: Add failing compiler tests for symmetry, permutation invariance, sparse unrated accounting, candidate-set mismatch, exact source event IDs, no transitive reduction, budget scaling, diagnostics, fingerprints, and zero-edge status.
- [x] Step 10: Run existing Phase 4 decision-feedback and app tests before production edits.

**Verification:**

- [x] New tests fail only because Phase 5 policy, provenance, and compiler behavior are absent.
- [x] Existing Phase 4 tests remain green before production edits.
- [x] No production file changes occur in this task.

**Exit Criteria:** impact is understood and acceptance tests describe every admissible and invalid case.

### Task 2: Extend compiler policy through existing SSOT

**Purpose:** add exact Phase 5 semantics without creating a second config owner.

**Files:**

- Modify: `config/policy/decision_learning.yaml`
- Modify: `src/fitcv/decision_feedback.py`
- Inspect only unless tests prove a loader gap: `src/fitcv/config.py`
- Modify: `tests/test_config.py`
- Modify: `tests/test_decision_feedback.py`

**Preconditions:**

- Task 1 failing policy tests exist
- Impact check for `validate_decision_learning_policy` is complete

**Steps:**

- [x] Step 1: Add exact `preference_compiler` block with version `preference-compiler-v1`, minimum gap `2`, weights `1.0..4.0`, and budget `12.0`.
- [x] Step 2: Extend top-level exact-key validation to require compiler block.
- [x] Step 3: Validate exact compiler keys, integer gap `1..4`, exact weight keys `1..4`, finite positive strictly increasing weights, and finite positive budget.
- [x] Step 4: Normalize compiler values into validated policy before full policy fingerprinting.
- [x] Step 5: Compute compiler-policy fingerprint only from normalized compiler block through existing fingerprint helper.
- [x] Step 6: Preserve and expose existing full `decision_learning_policy_fingerprint`; require rating-label semantic changes to bump rating-scale version.
- [x] Step 7: Keep `src/fitcv/config.py` unchanged unless a failing test proves current loader delegation is insufficient.
- [x] Step 8: Make focused config and policy tests green.

**Verification:**

- [x] `python -m pytest tests/test_config.py tests/test_decision_feedback.py -q -k "policy or config"`
- [x] Source search finds one policy-file owner and no settings/UI shadow.
- [x] Existing `decision_learning_policy_fingerprint` changes when compiler values change.

**Exit Criteria:** exact compiler semantics load from one policy file and no dead config exists.

### Task 3: Add canonical provenance reducer and candidate identity helper

**Purpose:** expose event provenance and candidate compatibility without duplicating Phase 4 logic.

**Files:**

- Modify: `src/fitcv/decision_feedback.py`
- Modify: `tests/test_decision_feedback.py`
- Verify unchanged consumer behavior: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_worker_job.py`

**Preconditions:**

- Task 2 policy tests pass
- Impact checks for `reduce_rating_events` and `build_decision_feedback_source` are complete

**Steps:**

- [x] Step 1: Add frozen `EffectiveRatingState` with rating, source event ID, and event sequence.
- [x] Step 2: Add one canonical state reducer accepting optional nonnegative watermark; `None` means all persisted events for current UI state.
- [x] Step 3: Reject selected events without sequence, duplicate selected event IDs, and duplicate selected sequences.
- [x] Step 4: Preserve latest set or clear event by highest `event_sequence`; ignore timestamps and UUID ordering.
- [x] Step 5: Reimplement `reduce_rating_events(...)` as a small projection over canonical states, preserving its current return contract.
- [x] Step 6: Extract existing candidate-set canonical payload/fingerprint construction into one private shared helper.
- [x] Step 7: Reuse helper in `build_decision_feedback_source(...)` and `build_episode_records(...)` without changing v4 fingerprints.
- [x] Step 8: Add regression proof that pre-refactor fixture fingerprints remain exact.
- [x] Step 9: Make reducer, source-builder, persisted-source, and app-current-state tests green.

**Verification:**

- [x] `python -m pytest tests/test_decision_feedback.py tests/test_fitcv_cp/test_app.py -q -k "decision_feedback or rating"`
- [x] Existing Phase 4 source and episode fingerprints remain unchanged for same evidence.
- [x] UI still receives `unrated | 1 | 2 | 3 | 4 | 5` values.
- [x] Source search finds one latest-event algorithm and one candidate-set fingerprint builder.

**Exit Criteria:** Phase 4 and Phase 5 share one reducer and one candidate identity path.

### Task 4: Implement pure symmetric preference compiler

**Purpose:** produce deterministic weighted edge sets for every compatible episode snapshot.

**Files:**

- Modify: `src/fitcv/decision_feedback.py`
- Modify: `tests/test_decision_feedback.py`

**Preconditions:**

- Task 3 canonical reducer and candidate identity helper pass
- No persistence or runtime surface is needed

**Steps:**

- [x] Step 1: Add frozen `PreferenceEdge`, `PreferenceCompilerDiagnostics`, and `PreferenceCompilerResult` records.
- [x] Step 2: Add exact schema/version/status constants owned by code.
- [x] Step 3: Validate nonnegative watermark, episode/policy domain and scale, unique alternatives/ranks, candidate-set fingerprint, selected event episode/alternative/scale, and compiler policy.
- [x] Step 4: Filter events through watermark and derive canonical effective states for every alternative; missing event becomes ephemeral unrated with null provenance.
- [x] Step 5: Sort rated states by alternative ID and enumerate rated unordered pairs with `itertools.combinations`.
- [x] Step 6: Compute total and unrated pair counts with integer formulas; place every rated pair in equal, below-gap, or emitted bucket.
- [x] Step 7: Orient emitted edge higher rating to lower rating; attach exact ordered source set-event IDs and configured gap weight.
- [x] Step 8: Preserve every qualifying pair; add no transitive reduction, sampling, or edge cap.
- [x] Step 9: Compute raw weight sum, one common episode scale, bounded edge weights, and reconciled diagnostics.
- [x] Step 10: Build compiler-input fingerprint from episode, candidate set, watermark, full decision-learning policy, compiler policy, and sorted effective provenance.
- [x] Step 11: Build edge-set fingerprint from canonical ordered edges; exclude diagnostics from identity.
- [x] Step 12: Return `compiled` for nonempty edges and `insufficient_evidence` for valid empty sets; raise `ValueError` for malformed/incompatible input.
- [x] Step 13: Make exhaustive, symmetry, permutation, watermark, budget, provenance, and fingerprint tests green.

**Verification:**

- [x] `python -m pytest tests/test_decision_feedback.py -q`
- [x] All 36 pair cases pass.
- [x] Swapping and permuting inputs preserves canonical result.
- [x] Ratings `5,3,1` emit all three qualifying edges.
- [x] One-edge weights preserve `2.0 < 3.0 < 4.0`.
- [x] Alternate valid minimum gap, weight mapping, and budget change output and fingerprints without code branches.
- [x] Over-budget episode sum is at most `12.0` within asserted float tolerance.
- [x] Repeated compile from same watermark is structurally equal with identical fingerprints.

**Exit Criteria:** compiler result is Phase 6-ready and contains no solver or persistence behavior.

### Task 5: Reconcile source docs and generated metadata

**Purpose:** document compiler boundary without claiming learning, activation, or ranking use.

**Files:**

- Modify: `docs/configuration.md`
- Modify: `docs/architecture.md`
- Modify: `docs/pipeline.md`
- Modify: `docs/stages/ranking.source.yaml`
- Modify: `docs/features/cv_system/feature.source.yaml`
- Generate: `docs/stages/ranking.yaml`
- Generate: `docs/features/cv_system/cv_system.yaml`
- Generate: `docs/features/cv_system/history.md`
- Generate: `docs/features/cv_system/lineage.generated.yaml`
- Generate: `docs/generated/architecture_dag.yaml`
- Generate: `docs/generated/capability_lineage.yaml`
- Generate: `docs/generated/planning_lineage.yaml`

**Preconditions:**

- Task 4 compiler tests pass
- Code shape and final capability ownership are known

**Steps:**

- [x] Step 1: Document compiler policy ownership, v1 values, and no-settings status.
- [x] Step 2: Document pure reducer-to-compiler handoff, watermark replay, edge semantics, episode cap, and Phase 6 boundary.
- [x] Step 3: Update ranking stage source as immutable evidence producer only; do not claim ranking consumes ratings or edges.
- [x] Step 4: Add `cv_system.preference-compilation` capability with code, tests, spec, plan, config, and doc evidence.
- [x] Step 5: Keep returned diagnostics under `cv_system.preference-compilation`; add no second feature capability or UI claim.
- [x] Step 6: Add matching code `@meta` capability linkage and test proof metadata required by validators.
- [x] Step 7: Regenerate architecture and planning outputs through canonical scripts.
- [x] Step 8: Check private/public boundary; publish nothing through public workflow in this phase.

**Verification:**

- [x] `python tools/docs/generate_architecture_metadata.py`
- [x] `python scripts/generate_planning_lineage.py`
- [x] `python tools/docs/generate_architecture_metadata.py --check`
- [x] Active capability lineage is complete with no exceptions.
- [x] Generated files contain no manual edits.

**Exit Criteria:** source docs and managed discovery agree on compiler-only behavior.

### Task 6: Run final verification and close plan

**Purpose:** prove Phase 5 completeness, regression safety, and bounded scope.

**Files:**

- Verify: all plan targets
- Modify only for closeout metadata: this plan
- Generate after completion metadata: managed histories and planning lineage

**Preconditions:**

- Tasks 1 through 5 complete
- No unresolved P1/P2 review findings

**Steps:**

- [x] Step 1: Run focused config, domain, app, store, SQLite, pipeline, parity, and ranking suites.
- [x] Step 2: Run Ruff and isolated mypy on Phase 5 domain/test files.
- [x] Step 3: Run architecture, planning, hook, repo-contract, and diff gates.
- [x] Step 4: Run scope searches proving no solver, persistence, route, settings, activation, learned vector, or ranking effect.
- [x] Step 5: Run GitNexus `detect_changes`; treat stale output as advisory and source/tests as authoritative.
- [x] Step 6: Review final diff for duplicate reducers, duplicate candidate identity, dead config, generated-file ownership, public-boundary leakage, and `.tmp-tests/` changes.
- [x] Step 7: Record exact test counts, validation output, GitNexus scope, audit disposition, failure-ledger disposition, and rollback status.
- [x] Step 8: Set plan `status: completed` only after every proof passes.
- [x] Step 9: Regenerate architecture history and planning lineage after completion metadata, then rerun lifecycle gates.

**Verification:**

- [x] Top-level Verification commands pass from fresh state.
- [x] Every task checkbox is complete or explicitly dropped with reason.
- [x] Plan contains `completed_at`, `change_id`, verification metadata, outcome summary, and closeout evidence.

**Exit Criteria:** Phase 5 is complete, replayable, source-derived, and ready for Phase 6 solver specification.

## Verification

Focused behavior and regressions:

```text
python -m pytest tests/test_config.py tests/test_decision_feedback.py -q
python -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_store.py -q -k "decision_feedback or admin_route_manifest"
python -m pytest tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py -q
python -m pytest tests/test_ranking.py tests/test_ranking_contract.py tests/test_ai_score.py -q
```

Code quality:

```text
python -m ruff check src/fitcv/decision_feedback.py tests/test_decision_feedback.py
uvx mypy src/fitcv/decision_feedback.py --show-error-codes --follow-imports=skip
```

Managed docs and repo gates:

```text
python tools/docs/generate_architecture_metadata.py
python scripts/generate_planning_lineage.py
python tools/docs/generate_architecture_metadata.py --check
python scripts/validate_planning_lifecycle.py
python scripts/hooks/run_validator.py --fast
python scripts/validate_repo_contracts.py --fast
git diff --check
```

Scope exclusion proof:

```text
rg -n "cvxpy|numpy|CLARABEL|solver|preference_vector|policy_activation|CREATE TABLE|@app\.(get|post)" src/fitcv/decision_feedback.py
rg -n "preference_compiler" src/fitcv_cp/settings_schema.py src/fitcv_cp/templates/settings.html
rg -n "compile_preference_edges|EffectiveRatingState|PreferenceEdge|PreferenceCompilerResult" src/fitcv tests
```

Expected:

- first two searches return no forbidden Phase 5 surface
- final search finds one compiler implementation, one reducer state contract, and focused tests
- legitimate spec/plan text may name deferred Phase 6 exclusions only

Authority proof:

```text
rg -n "preference-compiler-v1|minimum_rating_gap|gap_evidence_weights|max_episode_evidence_budget" config src/fitcv
rg -n "reduce_rating_event_states|reduce_rating_events" src/fitcv src/fitcv_cp
rg -n "candidate_set_fingerprint" src/fitcv/decision_feedback.py
```

Expected:

- policy YAML owns mutable values
- code owns exact keys, types, schemas, records, validation, and algorithms
- one state reducer backs value projection and compiler
- one candidate-set helper backs source creation, persisted validation, and compiler

Rollback notes:

- Phase 5 adds no persistence or runtime activation, so rollback is code/config/docs only
- rating ledger and v4 run artifacts remain unchanged
- if compiler policy is rolled back, keep Phase 4 rating policy and reducer behavior intact
- no edge migration or data deletion exists

## Closeout Evidence

- focused domain/config suite: `150 passed`
- app/store/SQLite/worker regression: `7 passed, 607 deselected`
- pipeline and resume parity: `142 passed`
- ranking regression: `65 passed, 1 skipped`
- code quality: Ruff passed; isolated mypy reported no issues
- managed docs and repo gates: architecture generation/check, planning-lineage generation, planning lifecycle, fast validator, repo contracts, and `git diff --check` passed after regeneration
- scope exclusion: no CVXPY/NumPy/solver, persistence, route, settings shadow, policy activation, learned vector, or ranking effect in Phase 5 compiler module
- authority proof: policy YAML owns mutable compiler values; one reducer owns effective rating state; one candidate-set helper owns identity across source creation, persisted validation, and compiler checks
- GitNexus changed-scope report: `HIGH` risk, `153` changed symbols, `9` affected processes, `18` changed files, expected shared-policy/candidate-identity fan-out; source/tests/regressions cover affected paths
- generated ownership: architecture DAG, capability lineage, planning lineage, feature/stage contracts, and feature lineage regenerated from source
- intentionally unchanged: `src/fitcv/config.py`, persistence schema, routes, workers, settings UI, solver/optimizer, ranking runtime, application tracker, public publication boundary, and `.tmp-tests/`
- audit evidence mandate: allowed bypass; no persistent test failure, live-run failure, data anomaly, security failure, or unclear contract drift remained after targeted syntax correction and fresh verification
- failure-ledger disposition: no reusable memory update needed; `apply_patch` denial was Windows-environment-local and exact replacement plus fresh tests verified the minimal fix
- rollback: no migration or edge persistence exists; revert code/config/docs while retaining Phase 4 append-only rating evidence
## Completion Criteria

Phase 5 is complete when:

1. all Key Deliverables and task Exit Criteria are satisfied
2. exact compiler policy loads from one SSOT and no settings/env shadow exists
3. one provenance reducer owns latest-event selection and UI projection remains compatible
4. one candidate-set identity helper owns source, persisted validation, and compiler checks
5. every unordered pair follows one exhaustive symmetric decision table
6. unrated, equal, and below-gap pairs create no edge
7. every qualifying pair creates exactly one directed edge with exact source event IDs
8. one episode scale caps total evidence without normalizing small episodes to one
9. canonical input and edge-set fingerprints are deterministic and watermark-bound
10. valid empty edge sets return `insufficient_evidence`
11. malformed or incompatible inputs fail closed
12. Phase 3 ranking and Phase 4 UI/ledger behavior remain unchanged
13. no DB, API, worker, stage, settings, solver, learned vector, evaluation, activation, or new dependency exists
14. source docs and generated metadata are current
15. GitNexus changed-scope detection is recorded before commit
16. all Verification commands pass
17. plan is `completed` with terminal outcome and fresh evidence
18. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/superpowers/specs/2026-07-16-02-18-fitcv-inverse-optimization-phase-5-symmetric-preference-compiler-spec.md`
- `docs/superpowers/specs/2026-07-14-22-25-fitcv-inverse-optimization-master-ssot-symmetry-spec.md`
- `docs/superpowers/specs/2026-07-16-00-19-fitcv-inverse-optimization-phase-4-decision-feedback-spec.md`
- `docs/superpowers/plans/2026-07-16-00-41-fitcv-inverse-optimization-phase-4-decision-feedback-plan.md`
- `config/policy/decision_learning.yaml`
- `src/fitcv/decision_feedback.py`
- `docs/operating_system/governance/repo-governance.md`
- `docs/operating_system/lifecycle/doc-system-lifecycle.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
