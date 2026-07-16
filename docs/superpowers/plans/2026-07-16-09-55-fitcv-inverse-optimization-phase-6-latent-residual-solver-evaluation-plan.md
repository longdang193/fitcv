---
layer: change
artifact_type: plan
status: completed
completed_at: 2026-07-16T10:54:03+02:00
change_id: 2026-07-16-fitcv-inverse-optimization-phase-6-latent-residual-solver-evaluation
verification:
  - uv run --extra inverse-optimization python -m pytest tests/test_config.py tests/test_decision_feedback.py tests/test_inverse_optimization.py -q
  - uv run --extra inverse-optimization python -m pytest tests/test_ranking.py tests/test_ranking_contract.py tests/test_ai_score.py -q
  - uv run --extra inverse-optimization python -m pytest tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py -q
  - uv run --extra inverse-optimization python -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_worker_job.py -q -k "decision_feedback or admin_route_manifest"
  - python -m ruff check src/fitcv/decision_feedback.py src/fitcv/inverse_optimization.py scripts/run_inverse_optimization.py tests/test_inverse_optimization.py
  - uvx mypy src/fitcv/decision_feedback.py src/fitcv/inverse_optimization.py scripts/run_inverse_optimization.py --show-error-codes --follow-imports=skip
  - uv run --extra inverse-optimization python -c "import cvxpy as cp; assert 'CLARABEL' in cp.installed_solvers()"
  - python tools/docs/generate_architecture_metadata.py --check
  - python scripts/validate_planning_lifecycle.py
  - python scripts/hooks/run_validator.py --fast
  - python scripts/validate_repo_contracts.py --fast
  - uv lock --check
  - git diff --check
outcome:
  summary: Completed Phase 6 offline latent-residual learning with one decision-learning policy SSOT, complete compatible episode replay through the Phase 5 compiler, bounded CVXPY and CLARABEL solve with independent post-checks, episode-grouped evaluation, strict atomic JSON CLI, and no persistence, activation, or runtime ranking effect.
template_id: implementation-plan
name: fitcv-inverse-optimization-phase-6-latent-residual-solver-evaluation-implementation
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-stage-authority-contract
parent_spec: docs/superpowers/specs/2026-07-16-09-31-fitcv-inverse-optimization-phase-6-latent-residual-solver-evaluation-spec.md
targets:
  - docs/superpowers/specs/2026-07-16-09-31-fitcv-inverse-optimization-phase-6-latent-residual-solver-evaluation-spec.md
  - config/policy/decision_learning.yaml
  - pyproject.toml
  - uv.lock
  - src/fitcv/decision_feedback.py
  - src/fitcv/inverse_optimization.py
  - scripts/run_inverse_optimization.py
  - tests/test_config.py
  - tests/test_decision_feedback.py
  - tests/test_inverse_optimization.py
  - tests/test_ranking.py
  - tests/test_ranking_contract.py
  - tests/test_ai_score.py
  - tests/test_pipeline.py
  - tests/test_pipeline_stage_resume_parity.py
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
related_features:
  - cv_system
related_stages:
  - ranking
---

# FitCV inverse optimization Phase 6 latent-residual solver and episode-grouped evaluation implementation plan

## Goal

Implement one offline latent-residual training and evaluation boundary over complete Phase 5 preference evidence:

```text
compatible immutable episode cohort
+ complete rating-event snapshots through one watermark
-> existing Phase 5 compiler per episode
-> one canonical full-refit inverse problem
-> CVXPY + CLARABEL solve from zero
-> independent plain-Python post-check
-> episode-grouped evaluation
-> typed JSON artifacts only
```

Execution boundaries:

- extend `config/policy/decision_learning.yaml`; add no second optimizer config
- reuse `DecisionEpisode`, `DecisionAlternative`, `DecisionRatingEvent`, `compile_preference_edges(...)`, and `build_contract_fingerprint(...)`
- keep all new domain behavior in one `src/fitcv/inverse_optimization.py` module
- keep JSON adaptation in one standard-library CLI
- use CVXPY only through optional `inverse-optimization` extra and explicit CLARABEL solver
- learn only bounded vector `p`; keep baseline weights, labels, thresholds, alpha, margin, and compiler semantics fixed
- fit from zero over complete compatible evidence; active parent is comparison-only
- split evaluation by episode, never edge
- add no DB table, route, worker, settings control, activation, rollback, runtime rank mutation, or application-history inference
- leave user-owned `.tmp-tests/` untouched
- write failing focused tests before each production behavior change
- treat stale GitNexus output as advisory; source, tests, and active docs remain authoritative

## Key Deliverables

### One extended decision-learning policy SSOT

Bump umbrella policy to `decision-learning-v2`, add exact `inverse_optimization` policy, preserve compiler-policy semantics and emitted edge payload, and keep CVXPY optional.

### One pure offline training module

Add immutable request/result records, compatible cohort construction, deterministic full-problem identity, one vectorized CLARABEL solve, and independent numerical validation in one module.

### One episode-grouped evaluation path

Evaluate zero residual, candidate, and compatible parent through one shared metric path with leakage-free folds, truthful audit status, and explicit location/language coverage.

### One standard-library CLI boundary

Expose `train` and `evaluate` from canonical JSON input to canonical JSON output with atomic file replacement and exact exit codes.

### Source-derived lifecycle evidence

Update owning feature/stage/docs, regenerate derived contracts and lineage, preserve Phase 3–5 runtime behavior, and record fresh closeout proof.

## Task/Wave Breakdown

### Task 1: freeze policy and optional dependency contracts

**Purpose:**
- add exact optimizer semantics and install boundary before solver code exists

**Files:**
- Inspect: `config/policy/decision_learning.yaml`
- Inspect: `src/fitcv/decision_feedback.py`
- Inspect: `pyproject.toml`
- Modify: `config/policy/decision_learning.yaml`
- Modify: `src/fitcv/decision_feedback.py`
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Modify: `tests/test_config.py`
- Modify: `tests/test_decision_feedback.py`
- Create: `tests/test_inverse_optimization.py`

**Preconditions:**
- Phase 5 plan is completed
- Phase 6 spec exact values are unchanged
- no runtime module may import solver packages

**Steps:**
- [x] Step 1: Add failing tests for exact `inverse_optimization` keys, values, nested types, finite bounds, solver identity, tolerances, and evaluation limits.
- [x] Step 2: Add failing tests proving optimizer-policy changes alter optimizer/full/compiler-input/edge-set fingerprints while preserving compiler-policy fingerprint and emitted edge payload.
- [x] Step 3: Bump umbrella policy to `decision-learning-v2` and extend `decision_learning.yaml` with exact `latent-residual-v1` policy from spec.
- [x] Step 4: Extend `validate_decision_learning_policy(...)` and add one reusable optimizer-policy fingerprint helper beside existing compiler fingerprint logic.
- [x] Step 5: Add `inverse-optimization = ["cvxpy>=1.9,<2"]` under project optional dependencies and regenerate `uv.lock`.
- [x] Step 6: Add import-isolation test proving `fitcv.decision_feedback`, ranking, pipeline, and control-plane imports do not import CVXPY or inverse solver.
- [x] Step 7: Verify CLARABEL is installed when optional extra is selected.

**Verification:**
- [x] `python -m pytest tests/test_config.py tests/test_decision_feedback.py tests/test_inverse_optimization.py -q -k "policy or dependency or import"`
- [x] `uv run --extra inverse-optimization python -c "import cvxpy as cp; assert 'CLARABEL' in cp.installed_solvers()"`
- [x] compiler-policy fingerprint and edge payload remain unchanged; full-policy-dependent fingerprints change under optimizer-only mutation

**Exit Criteria:**
- one policy file owns mutable optimizer numerics; optional solver dependency has no runtime import path

### Task 2: build immutable cohort and problem contracts

**Purpose:**
- convert one request into one validated, canonical, complete Phase 5 evidence problem before solver import

**Files:**
- Inspect: `src/fitcv/decision_feedback.py`
- Create: `src/fitcv/inverse_optimization.py`
- Modify: `tests/test_inverse_optimization.py`

**Preconditions:**
- Task 1 complete
- optimizer policy and fingerprints are stable
- Phase 5 compiler remains sole edge interpreter

**Steps:**
- [x] Step 1: Add module `@meta` for planned capability `cv_system.preference-learning` and use frozen dataclasses plus `StrEnum` only.
- [x] Step 2: Add failing construction tests for `InverseTrainingEpisode`, `InverseOptimizationRequest`, evaluation context records, parent reference, solver result, and evaluation result.
- [x] Step 3: Validate request schema, domain, watermark, `events_loaded_through_sequence >= event_watermark`, duplicate episode IDs, known endpoints, finite normalized embeddings, exact dimensions, and event membership before solver import.
- [x] Step 4: Canonically sort episodes, alternatives, and events; call `compile_preference_edges(...)` once per episode at request watermark.
- [x] Step 5: Require shared preference, ranking, baseline, embedding, rating-scale, compiler, and optimizer interpretation while leaving qualification/candidate/source fingerprints episode-local.
- [x] Step 6: Retain every compiled edge and every zero-edge episode diagnostic; reject mixed contracts as one `invalid_input` result instead of splitting or dropping episodes.
- [x] Step 7: Build cohort, aggregate edge-set, solver-options, and problem fingerprints with existing `build_contract_fingerprint(...)`; exclude evaluation context, parent, timestamps, diagnostics, order, and output path.
- [x] Step 8: Return typed `insufficient_evidence` before solver import when aggregate edge count is zero.
- [x] Step 9: Add permutation tests for episode, alternative, event, and edge input order.

**Verification:**
- [x] `python -m pytest tests/test_inverse_optimization.py -q -k "request or cohort or problem or fingerprint or permutation or insufficient"`
- [x] every episode compiler result matches direct Phase 5 compiler output
- [x] malformed or incompatible request produces no partial prepared problem

**Exit Criteria:**
- one canonical prepared problem represents every compatible admissible cohort without solver or evaluation special cases

### Task 3: implement bounded CLARABEL solve and post-check

**Purpose:**
- solve one fixed convex latent-residual problem and return only independently validated plain domain values

**Files:**
- Modify: `src/fitcv/inverse_optimization.py`
- Modify: `tests/test_inverse_optimization.py`

**Preconditions:**
- Task 2 complete
- prepared problem contains finite baseline deltas, embedding deltas, weights, and exact dimension

**Steps:**
- [x] Step 1: Add failing recoverable-direction, zero-direction, identical-embedding, collinear, contradictory, and weak-direction fixtures.
- [x] Step 2: Import CVXPY lazily inside offline solve path; return typed `solver_error` with install hint when package or CLARABEL is unavailable.
- [x] Step 3: Build one vectorized problem with variables only for `p` and per-edge nonnegative slack.
- [x] Step 4: Use fixed baseline deltas, fixed `learned_alpha`, Phase 5 bounded weights, L2 regularization, one L2 norm bound, `cp.CLARABEL`, configured `max_iter`, `warm_start=False`, and `verbose=False`.
- [x] Step 5: Map exact solver statuses to `optimal` or `solver_error`; reject inaccurate, infeasible, unbounded, exception, and unknown statuses.
- [x] Step 6: Recompute vector norm, every score difference, minimum slack, maximum violation, and objective with `math.fsum` and `math.sqrt`.
- [x] Step 7: Reject nonfinite values, wrong dimension, norm/constraint violation beyond `feasibility_absolute`, or objective mismatch beyond `numeric_equivalence_absolute`.
- [x] Step 8: Compute direction diagnostics with one-reference `O(edge_count * embedding_dimension)` collinearity check; add no pairwise matrix, NumPy wrapper, or custom optimizer.
- [x] Step 9: Strip CVXPY variables, expressions, problem objects, exceptions, and tracebacks from returned result.
- [x] Step 10: Add solver-status, missing-dependency, post-check-failure, and input-permutation tests.

**Verification:**
- [x] `uv run --extra inverse-optimization python -m pytest tests/test_inverse_optimization.py -q -k "solve or direction or contradiction or status or postcheck"`
- [x] recoverable synthetic case aligns vector with known direction
- [x] contradiction remains feasible through positive slack
- [x] only exact `optimal` plus passing post-check carries vector
- [x] permutations remain equivalent within `1e-6`

**Exit Criteria:**
- solver returns one typed noncandidate result or one fully checked bounded vector; no solver object crosses boundary

### Task 4: add episode-grouped evaluation

**Purpose:**
- measure candidate evidence without edge leakage, parent bias, or fabricated retrieval relevance

**Files:**
- Modify: `src/fitcv/inverse_optimization.py`
- Modify: `tests/test_inverse_optimization.py`

**Preconditions:**
- Task 3 complete
- full-result fingerprints match request and policy

**Steps:**
- [x] Step 1: Add failing tests for episode counts around LOEO boundary, grouped-fold boundary, sparse folds, missing context, and input permutations.
- [x] Step 2: Implement `evaluate_preference_residual(...)` with fewer-than-two, LOEO, and deterministic grouped-five-fold modes from policy.
- [x] Step 3: Assign folds by SHA-256 of evaluation version plus episode ID, then round-robin; assert disjoint train/validation IDs and one validation appearance per evaluable episode.
- [x] Step 4: Fit every fold from zero on train episodes only; never use parent vector as prior, warm start, constraint, or regularizer.
- [x] Step 5: Route zero residual, fold candidate, full candidate, and compatible parent through one shared score/metric helper.
- [x] Step 6: Compute pair agreement, margin satisfaction/violation, weighted regret, vector norms/stability, clipping frequency, and rank-change fraction.
- [x] Step 7: Aggregate coverage by baseline label, rating gap, location, and language without inventing missing values.
- [x] Step 8: Preserve retrieval audit as `not_available` or `unlabeled_inspection_only` with null recall until explicit relevance labels exist.
- [x] Step 9: Validate parent compatibility independently; report `not_provided`, `compatible`, or `incompatible` without failing candidate evaluation.
- [x] Step 10: Fingerprint fold assignments, metrics, coverage, audit state, and comparison state canonically.

**Verification:**
- [x] `uv run --extra inverse-optimization python -m pytest tests/test_inverse_optimization.py -q -k "evaluation or fold or parent or audit or coverage"`
- [x] no episode appears in both train and validation for one fold
- [x] every evaluable episode is validation exactly once
- [x] input order cannot change folds, metrics, or evaluation fingerprint
- [x] unlabeled audit recall remains null

**Exit Criteria:**
- evaluation is deterministic, episode-grouped, typed, comparison-symmetric, and promotion-neutral

### Task 5: add canonical JSON CLI adapter

**Purpose:**
- expose offline `train` and `evaluate` without creating service, persistence, or numeric override surfaces

**Files:**
- Create: `scripts/run_inverse_optimization.py`
- Modify: `tests/test_inverse_optimization.py`

**Preconditions:**
- Task 4 complete
- domain functions accept and return plain typed values

**Steps:**
- [x] Step 1: Add failing golden-fixture tests for `train`, `evaluate`, stdout, file output, malformed JSON, invalid domain data, missing parent, and each exit-code class.
- [x] Step 2: Build one `argparse` parser with `train` and `evaluate` subcommands, required domain/input arguments, optional parent/output arguments, and no numeric flags.
- [x] Step 3: Reuse `decision_feedback_source_v1` plus `build_episode_records(...)`; keep only rating-event/evaluation-context JSON adaptation in CLI and reject unknown keys.
- [x] Step 4: Load policy through existing canonical config path.
- [x] Step 5: Serialize dataclasses and enums to sorted compact JSON with standard library only.
- [x] Step 6: Write stdout when output is omitted; otherwise write temporary file in destination directory, close it, then atomically replace destination with `os.replace(...)`.
- [x] Step 7: Return exit `0` for optimal/evaluated/valid insufficient evidence, `2` for invalid input, and `3` for missing dependency or solver error.
- [x] Step 8: Ensure errors expose stable codes/messages without tracebacks in artifact payloads.

**Verification:**
- [x] `uv run --extra inverse-optimization python -m pytest tests/test_inverse_optimization.py -q -k "cli or json or exit or atomic"`
- [x] repeated golden input produces byte-identical JSON
- [x] interrupted/failed output path leaves existing destination unchanged
- [x] CLI contains no DB, HTTP, activation, rollback, or settings import

**Exit Criteria:**
- one standard-library CLI adapts external JSON at boundary and leaves domain module JSON-free

### Task 6: prove runtime and earlier-phase isolation

**Purpose:**
- prove Phase 6 adds offline evidence only and cannot alter production ranking or earlier contracts

**Files:**
- Verify: `src/fitcv/ranking.py`
- Verify: `src/fitcv/pipeline.py`
- Verify: `src/fitcv/decision_feedback.py`
- Verify: `tests/test_ranking.py`
- Verify: `tests/test_ranking_contract.py`
- Verify: `tests/test_ai_score.py`
- Verify: `tests/test_pipeline.py`
- Verify: `tests/test_pipeline_stage_resume_parity.py`
- Verify: `tests/test_decision_feedback.py`

**Preconditions:**
- Tasks 1–5 complete
- no production runtime caller has been added

**Steps:**
- [x] Step 1: Run Phase 3 ranking and label regression suites unchanged.
- [x] Step 2: Run Phase 4 rating/source/store/control-plane regressions unchanged.
- [x] Step 3: Run Phase 5 reducer/compiler and fingerprint regressions unchanged.
- [x] Step 4: Run pipeline and resume-parity regressions unchanged.
- [x] Step 5: Search runtime modules for inverse solver/CVXPY/CLARABEL imports and search Phase 6 files for persistence, route, worker, settings, or activation surfaces.
- [x] Step 6: Assert baseline score, `strong | stretch | skip`, shortlist, CV eligibility, and displayed run results remain byte/structure compatible in existing fixtures.

**Verification:**
- [x] `python -m pytest tests/test_config.py tests/test_decision_feedback.py -q`
- [x] `python -m pytest tests/test_ranking.py tests/test_ranking_contract.py tests/test_ai_score.py -q`
- [x] `python -m pytest tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py -q`
- [x] `python -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_store.py -q -k "decision_feedback or admin_route_manifest"`
- [x] runtime import and forbidden-surface searches return only expected offline/test/doc references

**Exit Criteria:**
- Phase 6 is unreachable from production runtime and Phase 3–5 contracts remain unchanged

### Task 7: reconcile source docs and generated lineage

**Purpose:**
- make offline preference learning discoverable without turning generated files into manual truth

**Files:**
- Modify: `docs/architecture.md`
- Modify: `docs/configuration.md`
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
- Tasks 1–6 complete
- implementation behavior and final symbol names are stable

**Steps:**
- [x] Step 1: Add planned `cv_system.preference-learning` capability to human-owned feature source with exact offline/no-activation boundary.
- [x] Step 2: Add ranking-stage participation as immutable evidence producer only; do not claim runtime personalized ranking.
- [x] Step 3: Document optimizer policy, optional extra, CLI commands, solver statuses, evaluation grouping, and Phase 7 handoff in exact cross-cutting docs.
- [x] Step 4: Add `@capability cv_system.preference-learning` to public Phase 6 domain entry points and `@proves` markers to focused tests.
- [x] Step 5: Run architecture and planning generators; never hand-edit generated contracts, lineage, DAG, or generated history block.
- [x] Step 6: Verify private/public boundary; publish nothing through public workflow in Phase 6.

**Verification:**
- [x] `python tools/docs/generate_architecture_metadata.py`
- [x] `python scripts/generate_planning_lineage.py`
- [x] `python tools/docs/generate_architecture_metadata.py --check`
- [x] active capability lineage is complete with no unexplained exception
- [x] generated files contain only source-derived changes

**Exit Criteria:**
- source docs describe actual offline behavior and all generated discovery surfaces are current

### Task 8: run final proof and close plan

**Purpose:**
- prove implementation completeness, bounded scope, and safe Phase 7 handoff

**Files:**
- Verify: all plan targets
- Modify after proof: `docs/superpowers/plans/2026-07-16-09-55-fitcv-inverse-optimization-phase-6-latent-residual-solver-evaluation-plan.md`
- Generate after completion metadata: `docs/generated/planning_lineage.yaml`
- Generate after completion metadata: `docs/features/cv_system/history.md`
- Generate after completion metadata: `docs/features/cv_system/lineage.generated.yaml`

**Preconditions:**
- Tasks 1–7 complete
- no unresolved solver, evaluation, regression, or lifecycle failure

**Steps:**
- [x] Step 1: Run focused Phase 6 suite with optional solver extra.
- [x] Step 2: Run all earlier-phase regression and runtime-isolation suites.
- [x] Step 3: Run Ruff and isolated mypy on Phase 6 source, CLI, and test files.
- [x] Step 4: Run architecture, planning, hook, repo-contract, lock, and diff gates.
- [x] Step 5: Run scope searches proving no persistence, route, worker, settings, activation, runtime ranking effect, learned baseline weight, or parent-prior behavior.
- [x] Step 6: Run GitNexus `detect_changes`; treat stale output as advisory and source/tests as authoritative.
- [x] Step 7: Review final diff for duplicate policy values, duplicate edge interpretation, duplicate scoring metric paths, solver leakage, generated-file ownership, public-boundary leakage, and `.tmp-tests/` changes.
- [x] Step 8: Record exact test counts, dependency proof, solver versions/statuses, GitNexus scope, audit disposition, failure-ledger disposition, and rollback status.
- [x] Step 9: Set plan `status: completed` only after every proof passes; add `completed_at`, `change_id`, `verification`, and `outcome` metadata.
- [x] Step 10: Regenerate architecture history and planning lineage after completion metadata, then rerun lifecycle gates.

**Verification:**
- [x] top-level Verification commands pass from fresh state
- [x] every task checkbox is complete or explicitly dropped with reason
- [x] plan contains terminal metadata and fresh closeout evidence
- [x] Phase 7 handoff is persistence/activation/runtime only; no unfinished Phase 6 behavior is deferred

**Exit Criteria:**
- Phase 6 is complete, replayable, solver-isolated, leakage-safe, source-derived, and ready for Phase 7 lifecycle specification

## Verification

Focused Phase 6 proof:

```text
uv lock --check
uv run --extra inverse-optimization python -c "import cvxpy as cp; assert 'CLARABEL' in cp.installed_solvers()"
uv run --extra inverse-optimization python -m pytest tests/test_config.py tests/test_decision_feedback.py tests/test_inverse_optimization.py -q
python -m ruff check src/fitcv/decision_feedback.py src/fitcv/inverse_optimization.py scripts/run_inverse_optimization.py tests/test_inverse_optimization.py
uvx mypy src/fitcv/decision_feedback.py src/fitcv/inverse_optimization.py scripts/run_inverse_optimization.py --show-error-codes --follow-imports=skip
```

Earlier-phase and runtime isolation:

```text
python -m pytest tests/test_ranking.py tests/test_ranking_contract.py tests/test_ai_score.py -q
python -m pytest tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py -q
python -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_store.py -q -k "decision_feedback or admin_route_manifest"
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
rg -n "cvxpy|CLARABEL|installed_solvers" src/fitcv scripts -g "*.py"
rg -n "CREATE TABLE|ALTER TABLE|@app\.(get|post)|FastAPI|policy_activation|activate|rollback|active_policy|settings" src/fitcv/inverse_optimization.py scripts/run_inverse_optimization.py
rg -n "warm_start=True|parent.*prior|prior.*parent|learned_alpha.*Variable|baseline.*Variable" src/fitcv/inverse_optimization.py
rg -n "inverse_optimization|preference_vector" src/fitcv/ranking.py src/fitcv/pipeline.py src/fitcv/agentic_cv_analysis.py src/fitcv_cp
```

Expected:

- CVXPY/CLARABEL appears only in offline Phase 6 boundary and focused tests/docs
- no persistence, HTTP, worker, settings, activation, rollback, runtime rank mutation, learned baseline weight, learned alpha, or parent prior exists
- production ranking and control-plane modules have no inverse-optimization dependency

Authority proof:

```text
rg -n "latent-residual-v1|learned_alpha|preference_margin|preference_regularization|preference_vector_norm_bound|episode-grouped-v1" config src/fitcv
rg -n "compile_preference_edges|build_contract_fingerprint|evaluate_preference_residual" src/fitcv/inverse_optimization.py
rg -n "cv_system.preference-learning" src tests docs/features/cv_system/feature.source.yaml docs/stages/ranking.source.yaml
```

Expected:

- policy YAML owns mutable optimizer values
- existing Phase 5 compiler owns edge interpretation
- one Phase 6 module owns cohort, solver, post-check, and evaluation behavior
- one shared metric path evaluates baseline, candidate, and compatible parent
- one capability links source, tests, docs, and generated evidence

Rollback notes:

- Phase 6 adds no persistence or runtime activation, so rollback is code/config/dependency/docs only
- Phase 4 rating ledger, Phase 5 compiled evidence, and existing run artifacts remain unchanged
- removing optional extra and offline files restores pre-Phase-6 runtime behavior
- keep Phase 5 compiler policy and evidence contracts intact when rolling back optimizer block
- no DB migration, policy payload, activation history, or data deletion exists

## Completion Criteria

Phase 6 is complete when:

1. all Key Deliverables and task Exit Criteria are satisfied
2. exact optimizer policy loads from one SSOT
3. optimizer changes preserve compiler-policy fingerprint and Phase 5 edge payload while full-policy-dependent fingerprints change
4. CVXPY remains optional and runtime imports remain solver-free
5. one immutable request builds one compatible complete cohort
6. every episode is replayed through existing Phase 5 compiler at one watermark
7. mixed or malformed contracts fail closed before solver import
8. zero aggregate edges return typed `insufficient_evidence`
9. one vectorized CLARABEL problem learns only bounded vector `p` plus slack
10. contradictory evidence remains feasible and measurable
11. only exact `optimal` plus independent post-check carries candidate vector
12. solver errors and unsupported statuses return typed noncandidate results
13. episode-grouped evaluation has no train/validation leakage
14. baseline, candidate, and parent use one metric path
15. location/language coverage and unlabeled audit states remain truthful
16. CLI emits canonical JSON atomically with exact exit codes
17. no DB, API, worker, settings, activation, rollback, runtime ranking effect, or application-history inference exists
18. Phase 3 ranking, Phase 4 feedback, and Phase 5 compiler regressions pass
19. source docs and generated metadata are current
20. GitNexus changed-scope detection is recorded before commit
21. all Verification commands pass
22. plan is `completed` with terminal outcome and fresh evidence
23. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/superpowers/specs/2026-07-16-09-31-fitcv-inverse-optimization-phase-6-latent-residual-solver-evaluation-spec.md`
- `docs/superpowers/specs/2026-07-14-22-25-fitcv-inverse-optimization-master-ssot-symmetry-spec.md`
- `docs/superpowers/specs/2026-07-16-02-18-fitcv-inverse-optimization-phase-5-symmetric-preference-compiler-spec.md`
- `docs/superpowers/plans/2026-07-16-02-30-fitcv-inverse-optimization-phase-5-symmetric-preference-compiler-plan.md`
- `config/policy/decision_learning.yaml`
- `src/fitcv/decision_feedback.py`
- `docs/architecture.md`
- `docs/configuration.md`
- `docs/pipeline.md`
- `docs/stages/ranking.source.yaml`
- `docs/features/cv_system/feature.source.yaml`
- `docs/operating_system/governance/repo-governance.md`
- `docs/operating_system/lifecycle/doc-system-lifecycle.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
