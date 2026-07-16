---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: fitcv-inverse-optimization-phase-6-latent-residual-solver-evaluation
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-stage-authority-contract
parent_spec: docs/superpowers/specs/2026-07-14-22-25-fitcv-inverse-optimization-master-ssot-symmetry-spec.md
targets:
  - config/policy/decision_learning.yaml
  - pyproject.toml
  - uv.lock
  - src/fitcv/decision_feedback.py
  - src/fitcv/inverse_optimization.py
  - scripts/run_inverse_optimization.py
  - tests/test_config.py
  - tests/test_decision_feedback.py
  - tests/test_inverse_optimization.py
  - docs/architecture.md
  - docs/configuration.md
  - docs/pipeline.md
  - docs/stages/ranking.source.yaml
  - docs/features/cv_system/feature.source.yaml
related_features:
  - cv_system
related_stages:
  - ranking
---

# Detailed Spec: FitCV inverse optimization Phase 6 latent-residual solver and episode-grouped evaluation

## Goal

Learn the smallest bounded embedding-space preference residual supported by
Phase 5 ordinal preference edges while preserving Phase 3 baseline scores,
weights, labels, CV eligibility, and runtime behavior.

```text
one compatible immutable episode cohort
+ complete rating-event snapshots through one watermark
-> Phase 5 compiler replay per episode
-> one canonical full-refit inverse problem
-> CVXPY + CLARABEL offline solve from zero
-> independent plain-Python post-solve validation
-> episode-grouped held-out evaluation
-> typed solver and evaluation artifacts only
```

Phase 6 does not persist or activate policy, alter ranking, change
`strong | stretch | skip`, infer application history, learn baseline weights,
or introduce solver imports into runtime modules. Phase 7 owns persistence,
policy payloads, activation, rollback, runtime residual scoring, and observability.

## Triage

- layer: `change`
- feature type: `ADD`
- parent: inverse-optimization master SSOT and symmetry specification
- dependencies: completed Phase 3 baseline and Phase 5 compiler
- affected stage: `ranking` as immutable evidence producer only
- affected feature: `cv_system`
- implementation code: out of scope for this document
- implementation plan: required after approval
- generated refresh required during implementation: yes
- GitNexus: indexed commit predates Phase 5; advisory exploration only

```text
Layer: change
Feature type: ADD
Summary: Add one offline bounded latent-residual solver and leakage-safe evaluation boundary.
Affected stages: ranking (evidence only)
Affected features: cv_system
Spec needed: yes
Plan needed: yes, after approval
```

## Current-State Diagnosis

Reusable owners:

- `config/policy/decision_learning.yaml` owns rating/compiler semantics
- `DecisionEpisode` owns immutable ranking and embedding compatibility
- `DecisionAlternative` owns frozen baseline score, label, embedding, vector
  fingerprint, displayed rank, and stable alternative ID
- `DecisionRatingEvent` plus `reduce_rating_event_states(...)` own replay
- `compile_preference_edges(...)` owns canonical pairing, provenance, bounded
  weights, diagnostics, and edge fingerprints
- `build_contract_fingerprint(...)` owns canonical hashing
- Phase 2 shortlist artifacts own bounded deterministic below-cutoff audit rows

Missing boundary:

- inverse-optimization policy/fingerprint
- optional CVXPY dependency
- offline solver module and typed records
- compatible cohort validator and problem fingerprint
- independent post-solver checks
- episode-grouped evaluation
- standard-library train/evaluate CLI

## Key Deliverables

### Deliverable 1: one exact inverse-optimization policy extension

Bump `decision_learning_policy.policy_version` to `decision-learning-v2` and add
one exact block. Rating-scale and compiler versions stay unchanged. No second
optimizer file or settings/UI shadow.

```yaml
inverse_optimization:
  optimizer_version: latent-residual-v1
  learned_alpha: 0.05
  preference_margin: 0.02
  preference_regularization: 1.0
  preference_vector_norm_bound: 1.0
  solver:
    name: CLARABEL
    max_iter: 200
  numeric_tolerances:
    feasibility_absolute: 1.0e-7
    numeric_equivalence_absolute: 1.0e-6
  evaluation:
    evaluation_version: episode-grouped-v1
    leave_one_episode_out_max_episodes: 8
    grouped_fold_count: 5
```

Validation:

- exact keys at every level
- umbrella `policy_version == decision-learning-v2`
- `optimizer_version == latent-residual-v1`
- finite `learned_alpha` in `(0, 0.25]`
- finite `preference_margin` in `[0, 0.25]`
- finite positive regularization
- finite norm bound in `(0, 1]`
- solver name exactly `CLARABEL`
- integer `max_iter` in `1..10000`
- finite positive tolerances
- leave-one-out maximum integer at least `2`
- grouped fold count integer in `2..10`

`optimizer_policy_fingerprint` hashes only normalized optimizer block. Compiler
policy fingerprint remains compiler-block-only. Full decision-learning fingerprint
includes optimizer policy. Therefore optimizer-only changes leave emitted edge payload
and compiler-policy fingerprint unchanged, while full policy, compiler-input, and
edge-set fingerprints change because current Phase 5 identity includes full policy.

### Deliverable 2: one optional offline dependency boundary

```toml
[project.optional-dependencies]
inverse-optimization = ["cvxpy>=1.9,<2"]
```

Rules:

- optional extra only; base dependencies and `requirements.txt` stay unchanged
- `uv.lock` records extra
- runtime ranking, pipeline, control-plane, rating, and activation modules never
  import inverse solver, CVXPY, NumPy, or solver packages
- missing extra or missing CLARABEL returns typed `solver_error` with install hint
- implementation checks `CLARABEL` in `cvxpy.installed_solvers()`

Dependency evidence checked July 16, 2026: current CVXPY 1.9.x package metadata
supports Python 3.11+ including project Python 3.13, exposes CLARABEL, and supports
the conic L2-norm constraint. OSQP alone is not admissible for this model.

### Deliverable 3: plain immutable request records

Frozen dataclasses:

```text
InverseTrainingEpisode
  episode: DecisionEpisode
  alternatives: tuple[DecisionAlternative, ...]
  events: tuple[DecisionRatingEvent, ...]
  events_loaded_through_sequence: int
  evaluation_context: EvaluationEpisodeContext | null

InverseOptimizationRequest
  schema_version: inverse_optimization_request_v1
  domain_id
  event_watermark
  episodes: tuple[InverseTrainingEpisode, ...]

EvaluationAlternativeSlice
  alternative_id
  baseline_fit_label
  location_bucket
  language_bucket

RetrievalAuditContext
  audit_fingerprint
  sample_count
  cutoff_vector_similarity
  sampled_vector_similarities
  relevance_labels_available: false

EvaluationEpisodeContext
  episode_id
  alternative_slices
  retrieval_audit: RetrievalAuditContext | null

CompatibleParentReference
  parent_kind: zero_residual | learned
  domain_id
  parent_ref
  preference_vector
  baseline_policy_fingerprint
  ranking_contract_fingerprint
  embedding_contract_fingerprint
  embedding_dimension
  learned_alpha
```

Rules:

- nest existing Phase 4/5 records; do not redefine their truth
- JSON adaptation is CLI-only
- every episode records highest event sequence loaded from authoritative ledger
- `events_loaded_through_sequence >= request.event_watermark` is required
- future events above watermark may be present and stay ignored
- evaluation context never enters solver or problem fingerprint
- missing coverage/audit facts remain typed unknown/not-available
- parent is evaluation-only, never optimization prior
### Deliverable 4: one compatible cohort and full-refit problem

One request contains exactly one compatible cohort. Episodes share:

- domain and rating-scale version
- preference-context fingerprint
- ranking-contract and baseline-policy fingerprints
- embedding model, contract fingerprint, and dimension
- decision-learning/compiler interpretation

Qualification context remains episode-local and may differ. Candidate-set and
source-artifact fingerprints remain episode-local.

Construction:

1. validate request/policy before solver import
2. sort episodes by `episode_id`
3. sort alternatives/events canonically
4. call Phase 5 compiler for each episode at request watermark
5. retain every edge and all zero-edge episode diagnostics
6. return `insufficient_evidence` without solver when total edge count is zero
7. fit from zero over all compatible edges

Mixed contracts fail whole request as `invalid_input`; no silent split/drop.

Problem fingerprint:

```text
schema_version: inverse_problem_v1
domain_id
event_watermark
cohort_fingerprint
optimizer_policy_fingerprint
decision_learning_policy_fingerprint
baseline_policy_fingerprint
ranking_contract_fingerprint
embedding_model
embedding_contract_fingerprint
embedding_dimension
learned_alpha
preference_margin
preference_regularization
preference_vector_norm_bound
solver_name
solver_options_fingerprint
episodes[] sorted by episode_id:
  episode_id
  compiler_input_fingerprint
  edge_set_fingerprint
  candidate_set_fingerprint
```

Problem identity excludes evaluation context, parent vector, result,
diagnostics, timestamps, input order, and output path.

### Deliverable 5: one bounded CVXPY problem

For edge `i > j`:

```text
B_delta[e] = baseline_fit[i] - baseline_fit[j]
Z_delta[e] = embedding[i] - embedding[j]
w[e] = episode_bounded_weight[e]

minimize
  preference_regularization * sum_squares(p)
  + sum(w[e] * slack[e])

subject to
  B_delta[e] + learned_alpha * (Z_delta[e] @ p)
    >= preference_margin - slack[e]
  norm(p, 2) <= preference_vector_norm_bound
  slack >= 0
```

Rules:

- variables are only `p` and per-edge slack
- baseline and baseline weights remain constants
- Phase 5 bounded edge weights are used directly; no cohort renormalization
- one vectorized CVXPY problem, `cp.CLARABEL`, `max_iter` from policy,
  `warm_start=False`, `verbose=False`
- no custom optimizer, matrix wrapper, callbacks, nonlinear transform, learned
  alpha, learned baseline weight, active-parent prior, or incremental fit

### Deliverable 6: typed solver result and independent checks

```text
InverseOptimizationResult
  schema_version: inverse_optimization_result_v1
  status: optimal | insufficient_evidence | invalid_input | solver_error
  domain_id
  event_watermark
  cohort_fingerprint
  edge_set_fingerprint
  optimizer_policy_fingerprint
  decision_learning_policy_fingerprint
  problem_fingerprint
  candidate_preference_vector: tuple[float, ...] | null
  objective_value: float | null
  independently_recomputed_objective: float | null
  max_preference_violation: float | null
  preference_vector_norm: float | null
  vector_norm_residual: float | null
  embedding_model
  embedding_dimension
  embedding_contract_fingerprint
  learned_alpha
  solver_name
  solver_version
  solver_options_fingerprint
  raw_solver_status
  diagnostics
```

Status mapping:

| Boundary result | Status |
| --- | --- |
| zero compiled edges | `insufficient_evidence` |
| request/policy/cohort validation failure | `invalid_input` |
| missing solver, exception, infeasible, unbounded, inaccurate, unknown status, or failed post-check | `solver_error` |
| exact `optimal` plus passing post-check | `optimal` |

Only `optimal` carries vector.

Independent validation uses `math.fsum` and `math.sqrt`:

- vector finite, exact dimension
- norm within bound plus post-solve tolerance
- recompute every raw edge score difference
- recompute violation `max(0, margin - score_difference)`
- recompute minimum slack and objective
- compare solver and recomputed objectives with
  `abs_delta <= numeric_equivalence_absolute * max(1, abs(objective))`
- use `feasibility_absolute` only for norm and constraint residual gates
- reject nonfinite objective, vector, norm, or residual

Positive violation is admissible because slack represents conflict.

Diagnostics:

- episode/edge counts and evidence-weight sums
- zero/nonzero direction counts
- unique normalized direction count
- `direction_span_status: none | single_direction | collinear | multiple_directions`
- raw solver status/timing
- stable error code without persisted traceback

Collinearity uses one reference nonzero direction and checks every other normalized
direction against it in `O(edge_count * embedding_dimension)`. No pairwise matrix,
SVD, NumPy wrapper, or quadratic direction scan exists.

### Deliverable 7: episode-grouped evaluation

```text
evaluate_preference_residual(
  request,
  full_result,
  decision_learning_policy,
  parent_reference=None,
) -> PreferenceEvaluationResult
```

Mode selection:

- fewer than two episodes with edges: `insufficient_evidence`
- `2..leave_one_episode_out_max_episodes`: leave-one-episode-out
- larger cohort: deterministic grouped K-fold
- fold order uses SHA-256 of `evaluation_version + ":" + episode_id`, then
  round-robin distribution
- each episode is validation exactly once
- zero-train-edge or zero-validation-edge fold stays unevaluable diagnostic
- time-ordered drift evaluation deferred until versioned drift policy exists

Every evaluable fold fits from zero on train episodes and evaluates held-out
edges against zero residual, fold candidate, and compatible parent when given.

```text
raw_score(a, p) = baseline_fit[a] + learned_alpha * dot(p, embedding[a])
score_difference = raw_score(preferred, p) - raw_score(other, p)
pair_agreement = score_difference > 0
margin_satisfied = score_difference + tolerance >= preference_margin
weighted_regret = weight * max(0, preference_margin - score_difference)
```

Aggregate metrics:

- pair agreement, margin satisfaction/violation, weighted regret
- full/fold vector norms and vector stability
- raw personalized-score clipping frequency
- rank-change fraction vs baseline order
- coverage by baseline label, rating gap, location, and language
- retrieval audit sample count, cutoff/similarity range, and fingerprint

Vector stability: both zero -> `1.0`; exactly one zero -> `0.0`; otherwise
cosine. Ranking uses raw score and `alternative_id` tie-breaker. Clipping is
measurement only.

Phase 2 audit rows have no relevance labels. Phase 6 returns:

```text
retrieval_audit_status: not_available | unlabeled_inspection_only
retrieval_recall: null
```

No similarity-only recall claim.

```text
PreferenceEvaluationResult
  schema_version: preference_evaluation_result_v1
  status: evaluated | insufficient_evidence | invalid_input | solver_error
  evaluation_version
  evaluation_mode
  cohort_fingerprint
  full_problem_fingerprint
  parent_comparison_status: not_provided | compatible | incompatible
  fold_results
  aggregate_metrics
  coverage
  retrieval_audit
  evaluation_fingerprint
```

Phase 6 defines metrics, not activation thresholds.

### Deliverable 8: one standard-library offline CLI

```text
python scripts/run_inverse_optimization.py train \
  --domain ranking_v1 \
  --input <inverse-training-bundle.json> \
  [--output <solver-result.json>]

python scripts/run_inverse_optimization.py evaluate \
  --domain ranking_v1 \
  --input <inverse-training-bundle.json> \
  [--parent <compatible-parent.json>] \
  [--output <evaluation-result.json>]
```

Bundle reuses existing Phase 4 feedback-source payload instead of redefining
episode and alternative JSON:

```text
schema_version: inverse_training_bundle_v1
domain_id
event_watermark
episodes[]:
  feedback_source: decision_feedback_source_v1
  events_loaded_through_sequence: int
  rating_events[]:
    event_sequence: int
    event_id
    episode_id
    alternative_id
    event_type: set_rating | clear_rating
    rating: 1..5 | null
    rating_scale_version
    acted_by
    created_at: RFC3339 timestamp
  evaluation_context: object | null
```

Policy loads through canonical config. No numeric CLI override.

CLI rules:

- `argparse`, `json`, existing config loader
- `build_episode_records(...)` validates every `feedback_source`; CLI owns only rating-event and evaluation-context adaptation
- reject unknown/missing keys at every bundle level and require timezone-aware RFC3339 event timestamps
- canonical sorted compact JSON
- stdout when output omitted; atomic replace when writing file
- exit `0`: optimal/evaluated/valid insufficient evidence
- exit `2`: invalid input
- exit `3`: missing dependency/solver or solver error
- no activate/reject/rollback, DB access, or evidence mutation
## Detailed Solver Contract

### Validation order

Before CVXPY import/construction:

1. request schema/domain/nonnegative integer watermark
2. exact decision-learning and optimizer policy
3. nonempty unique episode IDs
4. complete-snapshot assertion
5. existing episode/alternative/event compatibility
6. one compatible cohort
7. Phase 5 compiler replay
8. finite baseline scores
9. finite normalized embeddings, dimensions, fingerprints
10. endpoint existence, canonical edge order, positive finite weights
11. optional parent compatibility

Invalid input records stable error code and no vector.

### Embedding validation

Every embedding must decode as finite numeric sequence, match cohort dimension,
have L2 norm within tolerance of `1.0`, and match vector fingerprint. Zero,
malformed, nonfinite, wrong-dimension, or fingerprint-mismatched evidence fails
closed. Never repair or renormalize frozen evidence.

### Determinism

Exact structural identity applies to normalized policy, cohort/episode/edge
ordering, fingerprints, and fold membership. Numeric solver values may vary only
within configured permutation tolerance; tests do not require byte-identical
floats.

### Parent comparison

- absent: baseline comparison only
- compatible: must match domain, baseline, ranking, embedding, dimension, alpha,
  and norm contracts
- incompatible: report and exclude parent metrics
- parent never changes training objective
- no persisted parent reference in Phase 6

## Admissible-Case Matrix

| Case | Training | Evaluation |
| --- | --- | --- |
| empty episodes | `invalid_input` | `invalid_input` |
| zero compiled edges | `insufficient_evidence` | `insufficient_evidence` |
| one episode with edges | possible `optimal` | held-out `insufficient_evidence` |
| compatible episodes | one full refit | grouped evaluation |
| mixed contracts | `invalid_input` | not run |
| differing qualification contexts | valid | episode-local coverage |
| loaded-through sequence below watermark | `invalid_input` | not run |
| future events above watermark | ignored | deterministic replay |
| nonfinite baseline | pre-solver `invalid_input` | not run |
| malformed/nonfinite/zero/wrong embedding | pre-solver `invalid_input` | not run |
| unknown edge endpoint | pre-solver `invalid_input` | not run |
| identical embeddings | feasible via slack; zero-direction diagnostic | valid if grouped evidence |
| collinear directions | solve; collinear diagnostic | stability exposes weakness |
| contradictory edges | feasible via slack | regret exposes conflict |
| zero useful direction | zero-centered/near-zero vector | weak-direction diagnostic |
| optional extra absent | `solver_error` | `solver_error` |
| CLARABEL absent | `solver_error` | `solver_error` |
| `optimal_inaccurate` | `solver_error` | no candidate metrics |
| unexpected infeasible status | `solver_error` | no candidate metrics |
| failed post-check | `solver_error` | no candidate metrics |
| permuted inputs | same fingerprints; numeric-equivalent result | same folds/metrics |
| parent absent | unaffected | baseline only |
| parent incompatible | unaffected | parent diagnostic |
| location/language missing | unaffected | unknown coverage |
| audit missing | unaffected | `not_available` |
| audit unlabeled | unaffected | inspection only; null recall |

## Task/Wave Breakdown

### Wave 1: freeze policy, dependency, and failing contracts

**Purpose:**
- lock optimizer semantics and offline boundary before solver code

**Steps:**
- [ ] add exact policy/fingerprint tests
- [ ] prove optimizer changes preserve compiler-policy fingerprint and edge payload while full-policy-dependent fingerprints change
- [ ] add optional-extra/runtime-isolation tests
- [ ] add failing request/result/cohort tests
- [ ] verify Python/CVXPY/CLARABEL support in CI

**Verification:**
- [ ] new tests fail only because Phase 6 is absent
- [ ] Phase 5 compiler tests stay green

**Exit Criteria:**
- policy/dependency choices are fixed without runtime leakage

### Wave 2: implement cohort and solver

**Purpose:**
- build one validated full-refit problem and typed result

**Steps:**
- [ ] add immutable records
- [ ] validate cohort and replay compiler per episode
- [ ] build canonical problem/fingerprints
- [ ] solve with CLARABEL
- [ ] independently recompute norm, residuals, objective
- [ ] cover zero-edge, contradiction, weak direction, invalid, solver failure

**Verification:**
- [ ] recoverable synthetic direction moves expected way
- [ ] contradictory evidence stays feasible
- [ ] invalid evidence fails before solver
- [ ] permutations preserve structure/numerics within tolerance

**Exit Criteria:**
- one plain result returns; no solver object crosses boundary

### Wave 3: add episode-grouped evaluation

**Purpose:**
- measure candidate without edge leakage or false retrieval claims

**Steps:**
- [ ] implement deterministic mode/folds
- [ ] fit folds from zero
- [ ] compute baseline/candidate/parent metrics
- [ ] compute stability, clipping, rank-change, coverage
- [ ] preserve unavailable/unlabeled audit states
- [ ] test sparse folds, incompatible parent, missing context

**Verification:**
- [ ] no episode is both train and validation in one fold
- [ ] every evaluable episode is validation once
- [ ] input order cannot change folds/metrics

**Exit Criteria:**
- evaluation is deterministic, grouped, typed, promotion-neutral

### Wave 4: add CLI and reconcile docs

**Purpose:**
- expose offline train/evaluate without runtime/persistence surfaces

**Steps:**
- [ ] add argparse CLI and JSON adapter
- [ ] add atomic output/exact exit codes
- [ ] document policy/dependency/solver/evaluation/Phase 7 handoff
- [ ] update ranking stage as evidence producer only
- [ ] add planned `cv_system.preference-learning` capability during implementation
- [ ] regenerate architecture/planning metadata

**Verification:**
- [ ] CLI golden fixtures produce canonical typed JSON
- [ ] runtime tests pass without solver extra
- [ ] repo/doc validators pass

**Exit Criteria:**
- Phase 6 runs offline and creates no active state

## Design Decisions

### Decision: extend existing decision-learning policy

- context: scale, compiler, optimizer, evaluation are one interpretation chain
- choice: one exact `inverse_optimization` block
- alternatives: new YAML; CLI numeric flags
- impact: one SSOT owns mutable Phase 6 numerics

### Decision: optional CVXPY with explicit CLARABEL

- context: L2 constraint requires maintained conic solver
- choice: `cvxpy>=1.9,<2` optional extra plus CLARABEL
- alternatives: custom optimizer; OSQP-only; runtime dependency
- impact: predefined solver, solver-free base runtime

### Decision: full refit from zero

- context: new-edge-only fit forgets retained preferences
- choice: complete replay and zero prior
- alternatives: incremental fit; active-parent prior
- impact: deterministic evidence interpretation

### Decision: fixed baseline and alpha

- context: first learned layer must not redefine explicit semantics
- choice: learn only bounded vector `p`
- alternatives: learn weights/alpha/thresholds
- impact: small explainable residual

### Decision: slack preserves contradiction

- context: valid user evidence may conflict
- choice: weighted nonnegative slack
- alternatives: delete conflicts; hard constraints
- impact: conflict becomes measurable regret

### Decision: evaluation groups by episode

- context: sibling edges are correlated
- choice: LOEO then deterministic grouped folds
- alternatives: edge split; unseeded random split
- impact: no episode leakage

### Decision: unlabeled audit is not recall

- context: Phase 2 audit has similarity/rank, not relevance
- choice: inspection metrics plus null recall
- alternatives: similarity-as-relevance; score audit rows
- impact: truthful evaluation and preserved Phase 2 isolation

### Decision: Phase 6 writes artifacts, not policy state

- context: lifecycle needs separate persistence/concurrency contract
- choice: typed JSON only; Phase 7 owns DB/activation
- alternatives: add snapshot/training tables now
- impact: solver proven before lifecycle mutation

## Invariants

1. `config/policy/decision_learning.yaml` remains sole mutable policy source for rating, compiler, optimizer, and evaluation semantics.
2. Optimizer configuration never changes existing compiler-policy fingerprint.
3. Phase 6 consumes only immutable, fingerprint-compatible decision episodes.
4. Every rating event is replayed through Phase 5 reducer and compiler; Phase 6 owns no second rating or edge interpretation path.
5. Cohort compatibility covers preference, ranking, baseline, embedding, rating-scale, compiler-policy, and optimizer-policy identity; qualification context remains validated episode-local evidence.
6. One cohort watermark selects one complete event prefix per episode.
7. Full fitting always uses every valid Phase 5 edge in selected cohort.
8. Edge, episode, event, and alternative order cannot change canonical fingerprints or semantic results.
9. Baseline weights, scores, fit labels, shortlist membership, CV eligibility, and ranking thresholds remain fixed.
10. Phase 6 learns only one bounded latent preference vector `p`.
11. `learned_alpha` remains fixed at `0.05`; Phase 6 does not optimize it.
12. Every preference edge uses same margin equation and slack treatment.
13. Contradictory valid edges remain admissible through nonnegative slack.
14. `||p||_2 <= 1.0` is enforced by solver and independently checked after solve.
15. Regularization and evidence weights use finite nonnegative configured values only.
16. Zero-edge cohorts return typed `insufficient_evidence` without invoking solver.
17. Malformed, nonfinite, dimensionally inconsistent, or incompatible inputs fail closed before solver invocation.
18. Only exact `optimal` status plus successful independent post-check produces candidate vector.
19. `optimal_inaccurate`, infeasible, unbounded, solver exceptions, and failed post-checks never produce activatable candidate.
20. CVXPY and CLARABEL remain optional offline dependencies; base runtime imports and ranking execution remain solver-free.
21. Solver-library objects never cross domain result boundary.
22. Active-parent data is evaluation-only and never becomes fitting prior, warm start, constraint, or regularizer.
23. Evaluation groups by episode; sibling edges never split across training and validation.
24. Every evaluable episode appears in validation exactly once.
25. Folds fit from zero using training episodes only.
26. LOEO applies through eight episodes; larger cohorts use deterministic five-fold episode grouping.
27. Baseline, candidate, and compatible parent use one common metric path.
28. Missing or unlabeled below-cutoff audit data cannot become fabricated relevance or recall.
29. Missing location or language context remains explicit unknown coverage; Phase 6 does not invent values or change hard-constraint behavior.
30. Evaluation reports evidence only and cannot activate, reject, or persist policy.
31. Phase 6 writes typed canonical JSON artifacts atomically and writes no DB state.
32. Same canonical input and policy produce same structural fingerprints, folds, statuses, and numerically equivalent results within declared tolerances.
33. Existing Phase 3, Phase 4, and Phase 5 behavior remains replayable and unchanged.

## Acceptance Criteria

- optimizer policy loader accepts exact v1 block and rejects missing, extra, nonfinite, negative, unsupported, or dimensionally invalid values
- optimizer-policy changes alter optimizer/full/compiler-input/edge-set fingerprints while preserving compiler-policy fingerprint and emitted edge payload
- base installation imports and runs existing ranking without CVXPY or CLARABEL
- inverse-optimization extra installs supported CVXPY range and exposes CLARABEL
- request, cohort, problem, solver-result, fold-result, and evaluation-result records are immutable plain domain values
- compatible episode permutations produce identical cohort/problem fingerprints
- incompatible policy, embedding, baseline, ranking, or rating contracts fail closed
- zero-edge cohort returns `insufficient_evidence` without solver invocation
- one-direction synthetic evidence produces bounded vector aligned with that direction
- identical embeddings remain feasible and produce explicit zero-direction diagnostics
- contradictory edges remain feasible and expose positive regret/slack
- collinear or weak directions remain typed and deterministic
- independent checks recompute vector norm, edge residuals, objective, and tolerances
- only exact `optimal` plus passing post-check returns candidate coefficients
- inaccurate, infeasible, unbounded, missing dependency, solver exception, and failed post-check return typed `solver_error` results
- endpoint, edge, event, alternative, and episode permutations preserve semantics within `1e-6` numeric tolerance
- evaluation never places one episode in both train and validation for one fold
- LOEO and grouped five-fold selection follow configured episode-count boundary
- every evaluable episode is held out exactly once
- fold training starts from zero and excludes active-parent influence
- baseline, candidate, and compatible parent metrics share one calculation path
- missing parent, incompatible parent, missing audit, unlabeled audit, and missing location/language context remain explicit typed states
- unlabeled audit rows report null recall rather than proxy relevance
- CLI uses `argparse`, validates canonical JSON, writes atomically, and returns documented exit codes
- Phase 6 creates no table, route, worker, settings UI, runtime rank mutation, policy activation, or application-history inference
- managed source docs and generated metadata validate after implementation

## Non-Goals

- learn or tune existing explicit ranking weights
- learn `learned_alpha`, margin, regularization, norm bound, rating-gap weights, normalization rules, fit-label thresholds, or CV thresholds
- replace Phase 5 edge compilation or persist compiled edges
- use active policy as optimizer prior or warm start
- perform online, incremental, stochastic, or per-edge optimization
- build custom solver, numerical linear-algebra layer, or evaluation framework
- activate, persist, version, roll back, or monitor learned policy
- change production ranking, shortlist order, `strong | stretch | skip`, or CV output
- add direct Job A versus Job B questions
- infer ratings, location, language, qualification, or application history
- treat missing context as negative evidence
- create relevance labels for Phase 2 audit rows
- promote or reject candidate automatically
- add HTTP routes, settings controls, JavaScript, background workers, or DB schema
- backfill or mutate old run artifacts
- implement Phase 7 lifecycle or Phase 8 operator rollout

## Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| optimizer policy becomes second compiler truth | extend one policy file; separate compiler and optimizer fingerprints |
| solver dependency leaks into runtime | optional extra, lazy offline import, runtime isolation tests |
| edge leakage inflates validation | group exclusively by episode and assert disjoint train/validation episode IDs |
| active parent biases candidate | comparison-only parent record; fit always starts from zero |
| contradictory ratings make problem unusable | one nonnegative slack variable per edge and weighted regret reporting |
| inaccurate solver result looks valid | reject `optimal_inaccurate`; independently recompute all feasibility checks |
| input order changes folds or numerics | canonical ordering, content fingerprints, deterministic fold assignment, tolerance tests |
| sparse evidence creates false confidence | typed `insufficient_evidence`, coverage metrics, stability diagnostics, no automatic promotion |
| embedding degeneracy hides weakness | zero-direction, collinearity, clipping, and weak-direction diagnostics |
| audit similarity is mistaken for relevance | preserve unlabeled state and emit null recall |
| candidate artifact becomes accidental policy | Phase 6 output contains no activation ID and writes no persistent active state |
| custom adapters duplicate native behavior | keep `argparse`, JSON, dataclasses, atomic file replacement, CVXPY, and CLARABEL at boundaries |

## Validation Plan

- proof target: one SSOT owns decision-learning numerics
  - method: config loader tests and source inspection
  - evidence: exact `inverse_optimization` block in `config/policy/decision_learning.yaml`; no duplicate numeric defaults
- proof target: Phase 5 semantics remain independent
  - method: change optimizer fields and rerun fingerprint tests
  - evidence: optimizer/full/compiler-input/edge-set fingerprints change while compiler-policy fingerprint and emitted edge payload remain identical
- proof target: runtime remains solver-free
  - method: base-environment import tests and dependency/source inspection
  - evidence: ranking and existing tests run without CVXPY; solver imports exist only in offline module path
- proof target: cohort construction is complete and deterministic
  - method: compatible/incompatible cohort matrix plus input permutations
  - evidence: identical canonical fingerprints for permutations; pre-solver rejection for contract mismatch
- proof target: optimization equation is implemented exactly
  - method: synthetic one-dimensional and multi-dimensional fixtures
  - evidence: expected direction, bounded norm, independently recomputed residuals and objective
- proof target: all admissible evidence remains representable
  - method: zero-edge, identical, collinear, contradictory, and weak-direction fixtures
  - evidence: typed result for each case; contradiction handled by slack rather than deletion or crash
- proof target: failed numerical states cannot escape as candidates
  - method: dependency absence, mocked statuses, solver exception, and post-check failure tests
  - evidence: exact typed failure status and absent candidate vector
- proof target: evaluation has no episode leakage
  - method: inspect every generated fold over boundary episode counts
  - evidence: disjoint train/validation IDs and every evaluable episode held out once
- proof target: evaluation comparisons are symmetric
  - method: run baseline, candidate, and parent through common metric fixtures
  - evidence: same metric schema and calculation path; parent absence/incompatibility remains diagnostic
- proof target: retrieval evidence remains truthful
  - method: evaluate missing and unlabeled audit fixtures
  - evidence: `not_available` or null recall until explicit labels exist
- proof target: CLI boundary is stable
  - method: golden JSON fixtures, malformed input tests, interrupted-write test, exit-code test
  - evidence: canonical typed JSON, atomic replacement, documented nonzero failures
- proof target: earlier phases remain unchanged
  - method: Phase 3 ranking, Phase 4 feedback, Phase 5 compiler, pipeline, parity, and store regression suites
  - evidence: existing outputs and fingerprints pass unchanged
- proof target: lifecycle documentation remains source-derived
  - method: architecture generation/check, planning-lineage generation, lifecycle validation, repo-contract validation, diff check
  - evidence: generated outputs current; no manual generated-file edits or public-boundary leakage

Recommended implementation verification:

```text
python -m pytest tests/test_config.py tests/test_decision_feedback.py tests/test_inverse_optimization.py -q
python -m pytest tests/test_ranking.py tests/test_ranking_contract.py tests/test_ai_score.py -q
python -m pytest tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py -q
python -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_store.py -q -k "decision_feedback or admin_route_manifest"
python -m ruff check src/fitcv/decision_feedback.py src/fitcv/inverse_optimization.py scripts/run_inverse_optimization.py tests/test_inverse_optimization.py
uvx mypy src/fitcv/decision_feedback.py src/fitcv/inverse_optimization.py --show-error-codes --follow-imports=skip
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
rg -n "cvxpy|clarabel|inverse_optimization|preference_vector" src/fitcv -g "*.py"
rg -n "CREATE TABLE|@app\.(get|post)|policy_activation|active_policy" src/fitcv/inverse_optimization.py scripts/run_inverse_optimization.py
```

Expected: solver dependency appears only at offline boundary; no persistence, route, activation, or production-ranking mutation appears in Phase 6.

## Completion Criteria

Phase 6 implementation is complete when:

1. all Key Deliverables and Acceptance Criteria pass
2. one policy file owns optimizer semantics without changing compiler identity
3. one canonical cohort builder replays complete Phase 5 evidence through one watermark
4. all compatible episodes fit one deterministic full-refit problem from zero
5. only one bounded latent vector is learned with fixed alpha, margin, and regularization
6. contradictory evidence remains feasible through measurable slack
7. all solver outputs pass independent norm, residual, objective, and status checks
8. every inadmissible or failed numerical case returns typed non-candidate result
9. episode-grouped evaluation proves no train/validation leakage
10. baseline, candidate, and compatible parent comparisons use one metric path
11. unlabeled audit and unknown context states remain explicit and truthful
12. CLI writes typed canonical JSON atomically with no persistent policy state
13. base runtime remains solver-free and existing ranking behavior remains unchanged
14. Phase 3 ranking, Phase 4 feedback, and Phase 5 compiler regressions pass
15. source docs and generated metadata are current
16. implementation plan is completed with fresh verification evidence
17. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
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
