---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: fitcv-inverse-optimization-master-ssot-symmetry
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-stage-authority-contract
targets:
  - config/policy/ranking.yaml
  - config/policy/decision_learning.yaml
  - pyproject.toml
  - uv.lock
  - src/fitcv/config.py
  - src/fitcv/ranking_contract.py
  - src/fitcv/ranking.py
  - src/fitcv/ai_score.py
  - src/fitcv/pipeline.py
  - src/fitcv/decision_feedback.py
  - src/fitcv/inverse_optimization.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/store.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/templates/run_detail_tab_enriched.html
  - scripts/run_inverse_optimization.py
  - docs/architecture.md
  - docs/configuration.md
  - docs/pipeline.md
  - docs/stages/ranking.source.yaml
  - docs/features/cv_system/feature.source.yaml
  - tests/test_decision_feedback.py
  - tests/test_inverse_optimization.py
  - tests/test_ranking.py
  - tests/test_ai_score.py
  - tests/test_pipeline.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_settings_schema.py
  - tests/test_fitcv_cp/test_store.py
  - tests/test_fitcv_cp/test_sqlite_store.py
related_features:
  - cv_system
  - admin_control_plane_core
  - inspection_debugging
  - settings_system
related_stages:
  - ranking
---

# Detailed Spec: FitCV inverse optimization master SSOT and symmetry

## Goal

Define one canonical, symmetric inverse-optimization system that learns personalized FitCV ranking policy from low-friction 1–5-star job ratings while preserving every user rating as ordinal source truth.

The system must behave uniformly across every admissible case, including no ratings, one rating, repeated or cleared ratings, equal ratings, ambiguous or clear rating gaps, incompatible contracts, partially identifiable evidence, contradictory evidence, solver failure, stale candidates, concurrent activation, and rollback.

The canonical flow is:

`RankingArtifact -> DecisionEpisode -> RatingEvent -> EffectiveRating -> PreferenceEdge -> InverseProblem -> CandidatePolicySnapshot -> Evaluation -> Activation`

Each arrow is a boundary adapter. No downstream layer recomputes or redefines upstream truth.

This master specification defines ownership, contracts, ordered phases, required child specifications, invariants, acceptance criteria, and validation evidence. It does not authorize implementation or a big-bang rewrite.

## Triage

- layer: `change`
- feature type: `ADD`
- summary: add one rating-driven inverse-policy learning system for ranking
- affected stages: `ranking`
- affected features: `cv_system`, `admin_control_plane_core`, `inspection_debugging`, `settings_system`
- spec needed: yes
- plan needed: no until this master spec and required child specs are approved

## Key Deliverables

### Deliverable 1: one SSOT ownership model

| Fact | Canonical owner |
| --- | --- |
| ranking feature names and computation semantics | `src/fitcv/ranking_contract.py` plus ranking feature functions |
| baseline numeric ranking policy | `config/policy/ranking.yaml` |
| decision-learning policy | `config/policy/decision_learning.yaml` |
| run-time ranking input vectors | immutable ranking stage artifact |
| frozen training alternatives | immutable decision-episode snapshot derived from ranking artifact |
| user judgment | append-only rating event ledger |
| current rating state | deterministic reduction of rating events |
| preference comparisons | deterministic compiler output |
| learned policy | immutable candidate or active policy snapshot |
| run-time policy selection | active snapshot resolver plus run-scoped policy fingerprint |
| activation and rollback history | append-only activation event ledger |

SSOT means one authority per fact, not one physical file for unrelated truths.

### Deliverable 2: one symmetric decision algebra

Every supported rating case normalizes through the same primitive:

`preferred alternative -> non-preferred alternative`

The compiler contains no UI-specific solver branches. It accepts effective ordinal ratings and produces deterministic weighted preference edges.

### Deliverable 3: one native-first rating and persistence path

Use native or already-owned components first:

- HTML forms, buttons, labels, and CSS
- existing FastAPI form handling
- `enum.IntEnum` and frozen `dataclasses.dataclass`
- `sqlite3` transactions, constraints, foreign keys, and indexes
- `json`, `hashlib`, `uuid`, `datetime`, and `argparse`
- existing config loader, run-store boundary, ranking artifacts, and job fingerprints

Do not recreate browser form behavior, database constraints, JSON encoding, hashing, UUID generation, timestamps, or argument parsing in custom frameworks.

### Deliverable 4: one bounded optimization dependency

Use CVXPY only in offline training/evaluation code. Runtime ranking, rating UI, event storage, effective-state reduction, and activation remain usable without importing CVXPY, NumPy, or solver packages.

First solver contract:

- CVXPY modeling layer
- one explicit QP solver selected by policy and validated in CI
- strictly convex L2 distance from baseline policy
- nonnegative per-edge slack
- simplex and configured weight bounds
- deterministic solver options
- typed statuses and independent residual validation

No custom optimizer is allowed while a maintained predefined solver correctly implements the convex program.

### Deliverable 5: one immutable policy lifecycle

Training produces a candidate only. Evaluation, activation, rejection, staleness, retirement, and rollback remain separate lifecycle events. Old runs keep the exact policy snapshot and fingerprint used originally.

### Deliverable 6: one explicit child-spec sequence

Required child detailed specs:

1. ranking policy and decision-learning contract SSOT
2. decision episode, rating ledger, and native star-rating surface
3. effective-rating reducer and deterministic preference compiler
4. CVXPY inverse solver and episode-grouped evaluation
5. policy snapshot registry, activation, rollback, and runtime use
6. observability, extension seam, docs, and closeout deletion

No implementation plan may combine phases before the required child spec exists and inherits this master spec.

## Current-State Diagnosis

### Existing reusable owners

- `src/fitcv/ranking.py`: six features and weighted final score
- `src/fitcv/ranking_contract.py`: weight and threshold validation
- `src/fitcv_cp/settings_schema.py`: control-plane setting metadata with duplicated ranking numeric defaults that must derive from canonical config
- `config/policy/ranking.yaml`: baseline ranking policy
- `src/fitcv/pipeline.py`: ranking rows and feature contributions
- ranking stage artifacts: run-scoped ranking evidence
- `src/fitcv/enrich.py::build_raw_job_fingerprint(...)`: stable job identity
- `src/fitcv/shortlist_runtime.py`: canonical hashing helpers
- `src/fitcv_cp/sqlite_store.py`: SQLite owner
- `src/fitcv_cp/store.py`: persistence boundary
- `src/fitcv_cp/templates/run_detail_tab_enriched.html`: larger job-review set
- `src/fitcv_cp/app.py`: native form POST and redirect patterns

### Existing SSOT violations to remove

Numeric ranking policy is duplicated across ranking YAML, Python fallback dictionaries, threshold defaults, settings-schema defaults, and tests. Final implementation keeps code-owned admissible feature names while making policy YAML the sole numeric baseline owner. Tests may use explicit fixtures but cannot become another production default authority.

### Existing gap

The project preserves ranking evidence but has no active application history or rating ledger. Historical preference cannot be reconstructed from past browsing. Learning starts from future explicit ratings only.

## Canonical Architecture

### Layer 1: ranking feature contract

Code owns supported feature names, order, direction, value range, computation, and missing-feature semantics. Policy config owns baseline weights, preference subweights, thresholds, missing-value defaults, and learnable bounds.

Canonical feature order:

1. `ai_score`
2. `must_have_match`
3. `vector_similarity`
4. `title_relevance`
5. `seniority_fit`
6. `preference_fit`

Feature order is emitted in the contract payload and fingerprint. Solver and compiler maintain no independent feature list.

### Layer 2: decision-learning policy

New canonical file: `config/policy/decision_learning.yaml`.

It owns versioned rating scales, minimum comparison gap, evidence weight by gap, domain binding, optimizer policy, solver policy, and activation policy. Exact numeric values belong to the Phase 1 child spec and config, not this master spec. Documentation references config keys instead of restating mutable values.

### Layer 3: decision episode

Episode fields:

```text
episode_id
domain_id
run_id
profile_fingerprint
feature_contract_fingerprint
baseline_policy_fingerprint
candidate_set_fingerprint
source_stage_artifact_fingerprint
created_at
```

Alternative fields:

```text
episode_id
alternative_id
displayed_rank
feature_vector_json
feature_vector_fingerprint
source_job_url
created_at
```

Rules:

- alternative identity is stable `raw_job_fingerprint`
- URL is descriptive metadata only
- feature vector is copied from immutable ranking artifact, never recomputed
- copied vector is provenance-bound archival evidence, not competing truth
- one episode contains one feature contract and profile context
- episode identity is deterministic from run and contract fingerprints
- first rating POST may materialize episode atomically when absent
- GET routes do not create or mutate episode state

### Layer 4: append-only rating event

```text
event_id
episode_id
alternative_id
event_type: set_rating | clear_rating
rating: 1 | 2 | 3 | 4 | 5 | null
rating_scale_version
acted_by
created_at
```

Database invariants:

- event rows are insert-only
- `set_rating` requires rating between 1 and 5
- `clear_rating` requires null rating
- alternative exists in episode
- rating scale matches episode domain contract
- event ordering uses `(created_at, event_id)`
- no mutable `current_rating` column exists as competing truth

### Layer 5: effective rating reducer

Effective rating is derived from the latest event for each `(episode_id, alternative_id)`.

Use SQLite ordering/window semantics or one shared Python reducer over ordered rows. Do not maintain a UI cache, JSON shadow state, or second current-state table.

Reducer outputs `unrated | 1 | 2 | 3 | 4 | 5`. `clear_rating` reduces to `unrated`.

### Layer 6: preference compiler

Compiler inputs:

- one compatible episode
- effective ratings
- versioned rating policy

Compiler edge:

```text
preferred_alternative_id
other_alternative_id
rating_gap
evidence_weight
episode_normalized_weight
source_event_ids
compiler_version
```

Canonical rule: `gap = higher_rating - lower_rating`.

| Case | Compiler output |
| --- | --- |
| both unrated | none |
| one unrated | none |
| same rating | none |
| gap below configured minimum | none |
| gap at or above configured minimum | one directed preference edge |
| incompatible contract/profile/scale | validation failure; no mixed cohort |

Equal ratings mean same ordinal band, not exact utility equality.

The compiler generates every rated pair meeting the configured gap. It does not use transitive reduction because slack, evidence weights, and margins make transitive deletion non-equivalent.

Episode normalization bounds total episode influence:

```text
episode_normalized_weight =
  gap_evidence_weight / sum(gap_evidence_weight for episode edges)
```

An empty edge set is valid and produces `insufficient_evidence`, not an error.

### Layer 7: inverse problem

For each edge `i > j`, `feature_difference = x_i - x_j`.

First implementation solves:

```text
minimize
  baseline_regularization * sum_squares(w - w0)
  + sum(edge_weight[e] * slack[e])

subject to
  feature_difference[e] @ w >= preference_margin - slack[e]
  sum(w) == 1
  lower_bounds <= w <= upper_bounds
  slack >= 0
```

Rationale:

- L2 baseline distance makes candidate weights unique under valid positive regularization
- slack keeps contradictory evidence feasible
- simplex preserves current weighted-score meaning
- bounds prevent unsupported weight collapse or dominance
- one explicit solver and option set makes execution reproducible enough for policy lifecycle

The boundary adapts plain Python values to solver-native arrays once. No application-specific matrix class is allowed.

### Layer 8: solver result

```text
status:
  optimal
  insufficient_evidence
  invalid_input
  infeasible_policy
  solver_error
candidate_weights
objective_value
max_constraint_violation
weight_sum_residual
bound_violation
solver_name
solver_version
solver_options_fingerprint
problem_fingerprint
```

`optimal_inaccurate` is not silently accepted. First implementation rejects it as candidate input unless a later policy explicitly changes that rule.

### Layer 9: evaluation

Edges from the same episode are correlated. Evaluation splits by episode, never random edge.

Evaluation modes:

- leave-one-episode-out when evidence is small but sufficient
- grouped train/validation split when more episodes exist
- time-ordered grouped evaluation when preference-drift evaluation is enabled

Required comparisons:

- candidate policy vs parent active policy
- held-out preference violation rate
- held-out weighted slack/regret
- weight stability across episode resamples
- feature-difference rank and conditioning diagnostics
- missing-feature/default-use coverage
- candidate weight delta from parent

Counts are prerequisites only. Edge count does not prove identifiability.

### Layer 10: immutable policy snapshots

```text
policy_snapshot_id
domain_id
feature_contract_fingerprint
baseline_policy_fingerprint
parent_policy_kind: baseline | learned
parent_policy_ref
status: candidate | active | rejected | stale | retired
weights_json
training_run_id
event_watermark
edge_set_fingerprint
compiler_version
optimizer_policy_fingerprint
solver_metadata_json
evaluation_json
created_at
activated_at
```

Rules:

- snapshots are immutable after creation except lifecycle status transition
- weights are never edited in place
- candidate references exact effective parent as either `baseline:<baseline_policy_fingerprint>` or `learned:<policy_snapshot_id>`
- candidate stores baseline policy fingerprint used to build feature and optimization context
- equivalent candidate within configured tolerance creates no new snapshot
- candidate becomes stale if rating inputs, compiler policy, feature contract, baseline policy, or effective parent changes before activation

### Layer 11: activation and rollback

Activation uses one SQLite transaction:

1. load candidate
2. verify candidate status is `candidate`
3. verify candidate parent reference equals current effective parent reference, whether baseline or learned
4. verify baseline, evidence, compiler, optimizer, and evaluation fingerprints remain current
5. retire previous active snapshot
6. activate candidate
7. append activation event
8. commit

Rollback uses the same mechanism with a previous validated snapshot as target. Concurrent activation uses compare-and-swap semantics. A stale candidate cannot replace newer active policy.

### Layer 12: runtime ranking integration

At run start:

1. load baseline ranking policy from config
2. resolve active learned snapshot for compatible domain, feature contract, and baseline policy fingerprint
3. if compatible snapshot exists, overlay only learned weight vector
4. validate effective weights through existing ranking contract
5. record snapshot ID and fingerprints in effective settings and ranking artifact
6. rank through normal `compute_final_score(...)`

Runtime ranking does not call optimizer and does not import CVXPY.

Fallback behavior:

- no active snapshot -> baseline config
- incompatible feature or baseline snapshot -> baseline config plus diagnostic
- invalid snapshot -> baseline config plus failure diagnostic
- persistence unavailable -> baseline config; no hidden memory-only active policy

## Admissibility Contract

An input is admissible when all of these conditions hold:

- domain ID and rating-scale version are supported by validated decision-learning policy
- each episode, when present, references an existing immutable ranking artifact and one profile context
- every alternative in an episode has unique stable identity and one feature vector matching canonical feature order
- all feature values are finite and satisfy feature-contract ranges or declared missing-value adaptation
- effective ratings are `unrated` or valid labels from episode scale
- every nonempty training cohort shares domain, profile context, feature contract, rating scale, compiler version, and optimizer policy
- baseline weights and configured bounds are finite, dimensionally complete, and simplex-feasible
- solver name and option set are supported by installed offline environment when a nonempty trainable problem reaches solver boundary

No evidence, one rating, equal ratings, below-gap ratings, contradictory preferences, or rank-deficient evidence are admissible states. They produce typed empty, diagnostic, or partially identified results through normal flow.

Malformed ratings, unknown alternatives, nonfinite features, mixed contracts, dimension mismatch, infeasible bounds, unsupported solvers, or corrupt fingerprints are invalid inputs. They fail at nearest owning boundary before optimization and never create a candidate.

Uniform handling means every admissible input follows same reduction, compilation, optimization-result, evaluation, and lifecycle interfaces. Uniform does not mean every state produces edges or candidate.

## Admissible-Case Matrix

| Case | Storage result | Compiler result | Training result | Activation effect |
| --- | --- | --- | --- | --- |
| no ratings | no events | no edges | insufficient evidence | none |
| one rating | one event | no edges | insufficient evidence | none |
| ratings differ by one | events retained | no edges | insufficient evidence unless older edges exist | none |
| ratings differ clearly | events retained | directed edges | eligible subject to gates | candidate only |
| equal ratings | events retained | no ordering | no equality constraint | none |
| rating changed | append new event | rebuild affected edges | old candidate may become stale | none until approval |
| rating cleared | append clear event | remove active rating edges | old candidate may become stale | none |
| contradictory episodes | events retained | contradictory edges retained | slack absorbs conflict | candidate evaluated normally |
| incompatible feature contracts | separate episodes/cohorts | no cross-contract edges | separate training | no mixed snapshot |
| incompatible rating scale | separate version cohort or validation failure | no mixed edges | separate training | none |
| zero compiled edges | valid empty set | empty | insufficient evidence | none |
| rank-deficient evidence | valid diagnostics | edges retained | regularized candidate marked partially identified | activation requires stability gate |
| infeasible bounds | config validation failure | not applicable | infeasible policy | none |
| solver failure | evidence retained | edges retained | solver error | active policy unchanged |
| candidate equals parent | evidence retained | edges retained | no-op | no snapshot churn |
| baseline or learned parent changes before activation | candidate retained | not applicable | candidate stale | activation blocked |
| old run viewed after new activation | original episode retained | original context retained | no mutation | old run stays reproducible |

## Native-First Boundary Rules

### Browser and HTML

- use native `<form method="post">`
- use five submit buttons or radio inputs with explicit labels
- preserve keyboard navigation and accessible names
- use CSS for star display
- use no custom JavaScript for rating submission
- use redirect-after-POST
- preserve current query, filter, page, and page-size through a validated redirect target

### FastAPI boundary

- accept form strings through existing `Form(...)`
- adapt once to `RatingValue(IntEnum)` or `clear_rating`
- reject invalid rating before persistence
- do not pass raw form strings into compiler or solver

### SQLite boundary

- use `CHECK`, `UNIQUE`, `FOREIGN KEY`, and indexes
- enable foreign-key enforcement on owned connections
- use transactions for episode materialization plus first event
- use transactions for activation and rollback
- use SQL ordering/window functionality for current rating queries where clear
- do not add an ORM or migration framework
- follow existing add-missing-table/column migration style

### JSON and hashing boundary

- use canonical `json.dumps(..., sort_keys=True, separators=(",", ":"))`
- reuse existing stable fingerprint helpers
- store structured JSON plus fingerprint where audit/replay requires it
- never compare Python object identity for contracts or policies

### Solver boundary

- keep compiler output as plain immutable Python records
- convert to NumPy only inside inverse solver
- return a plain immutable result record
- do not expose CVXPY variables or problems outside solver module

### CLI boundary

Use one standard-library `argparse` script:

```text
python scripts/run_inverse_optimization.py train --domain ranking_v1
python scripts/run_inverse_optimization.py evaluate --training-run <id>
python scripts/run_inverse_optimization.py activate --snapshot <id>
python scripts/run_inverse_optimization.py reject --snapshot <id>
python scripts/run_inverse_optimization.py rollback --snapshot <id>
```

No CLI framework dependency is allowed.

## Persistence Contract

### `decision_episodes`

```text
PRIMARY KEY episode_id
UNIQUE run_id, domain_id, feature_contract_fingerprint, candidate_set_fingerprint
```

### `decision_episode_alternatives`

```text
PRIMARY KEY episode_id, alternative_id
FOREIGN KEY episode_id -> decision_episodes
NOT NULL feature_vector_json
NOT NULL feature_vector_fingerprint
```

### `decision_rating_events`

```text
PRIMARY KEY event_id
FOREIGN KEY episode_id, alternative_id -> decision_episode_alternatives
CHECK event_type in set_rating, clear_rating
CHECK set_rating implies rating between 1 and 5
CHECK clear_rating implies rating is null
```

### `inverse_training_runs`

Required fields:

```text
training_run_id
domain_id
cohort_fingerprint
event_watermark
edge_set_fingerprint
compiler_version
optimizer_policy_fingerprint
baseline_policy_fingerprint
parent_policy_kind
parent_policy_ref
status
result_json
created_at
```

### `ranking_policy_snapshots`

```text
PRIMARY KEY policy_snapshot_id
NOT NULL baseline_policy_fingerprint
CHECK parent_policy_kind in baseline, learned
NOT NULL parent_policy_ref
status constrained to lifecycle enum
one active snapshot per domain, feature contract, and baseline policy fingerprint
```

One-active enforcement may use a SQLite partial unique index or transactional enforcement, but not a second application-state registry.

### `policy_activation_events`

```text
activation_event_id
domain_id
previous_snapshot_id
target_snapshot_id
action
acted_by
created_at
```


## Task/Wave Breakdown

Each phase requires its own approved child detailed specification before implementation. A child spec may refine local names and schemas, but it must inherit this master flow, ownership map, admissible-case algebra, and invariants. Later phases may inspect earlier artifacts, but they may not create a second owner for earlier truth.

### Phase 0: approve ownership and child-spec map

**Purpose:**
- close authority, sequence, and dependency questions before code changes

**Steps:**
1. approve this master specification as the parent design authority
2. confirm the six child-spec scopes and their target files
3. confirm `config/policy/ranking.yaml` as baseline numeric ranking-policy SSOT
4. confirm `config/policy/decision_learning.yaml` as learning-policy SSOT
5. confirm immutable ranking artifacts as feature-vector source
6. confirm SQLite as rating, training, snapshot, and activation ledger owner
7. record any deliberate deferral as a named non-goal, not an implicit branch

**Verification:**
- every mutable semantic fact has one named owner
- every generated or derived fact identifies its upstream owner
- no child spec owns another child spec's canonical fact

**Exit Criteria:**
- master spec is approved
- child-spec sequence is approved
- implementation remains blocked until Phase 1 child spec is approved

### Phase 1: consolidate ranking and decision-policy SSOT

**Purpose:**
- remove duplicated numeric defaults and define one versioned admissibility contract

**Primary targets:**
- `config/policy/ranking.yaml`
- `config/policy/decision_learning.yaml`
- `src/fitcv/config.py`
- `src/fitcv/ranking_contract.py`
- `src/fitcv/ranking.py`
- `src/fitcv/ai_score.py`
- `src/fitcv_cp/settings_schema.py`
- `tests/test_ranking.py`
- `tests/test_ai_score.py`
- `tests/test_fitcv_cp/test_settings_schema.py`

**Steps:**
1. inventory every production ranking weight, threshold, subweight, and missing-value default
2. move each baseline numeric value to `config/policy/ranking.yaml`
3. keep supported feature names, order, direction, ranges, and computation semantics in code
4. define decision-learning scale, comparison gap, edge weighting, bounds, optimizer, solver, evaluation, and activation policy in `config/policy/decision_learning.yaml`
5. adapt YAML values once through existing config loading and typed validation
6. make control-plane setting defaults derive from loaded canonical policy instead of copied module literals
7. remove Python fallback dictionaries and threshold constants that duplicate production numeric policy
8. emit canonical contract payloads and fingerprints from validated values
9. update tests to use explicit fixtures or canonical config, never copied production defaults

**Verification:**
- search proves no duplicate production numeric policy remains
- config validation rejects unknown features, missing required features, invalid bounds, nonpositive regularization, unsupported solver, and infeasible simplex bounds
- ranking behavior remains unchanged under baseline config

**Exit Criteria:**
- one baseline numeric owner exists
- one learning-policy owner exists
- all later persisted objects can reference stable policy and feature-contract fingerprints

### Phase 2: add decision episodes, event ledger, and native rating UI

**Purpose:**
- capture future user judgment without fabricating historical application or preference data

**Primary targets:**
- `src/fitcv/decision_feedback.py`
- `src/fitcv_cp/store.py`
- `src/fitcv_cp/sqlite_store.py`
- `src/fitcv_cp/app.py`
- `src/fitcv_cp/templates/run_detail_tab_enriched.html`
- `tests/test_decision_feedback.py`
- `tests/test_fitcv_cp/test_app.py`
- `tests/test_fitcv_cp/test_store.py`
- `tests/test_fitcv_cp/test_sqlite_store.py`

**Steps:**
1. add SQLite tables, constraints, foreign keys, indexes, and append-only repository methods
2. materialize one immutable episode from one ranking artifact and compatible context
3. use `raw_job_fingerprint` as `alternative_id`; preserve URL only as metadata
4. freeze feature vectors and provenance fingerprints from artifact values
5. add `set_rating` and `clear_rating` POST operations with redirect-after-POST
6. render accessible native 1–5 controls with HTML and CSS; require no JavaScript
7. validate form data and redirect targets at HTTP boundary
8. keep GET routes read-only
9. preserve unrated as unknown and show effective rating derived from ledger
10. verify `ControlPlaneStore` delegation and SQLite persistence; any future backend must fail explicitly until it implements the same contract

**Verification:**
- repeated rating changes append events and produce one deterministic effective value
- clear appends an event and returns effective state to unrated
- invalid ratings, unknown alternatives, incompatible episodes, and unsafe redirects are rejected
- first rating plus episode materialization is atomic
- no historical application or rating record is synthesized

**Exit Criteria:**
- user can rate any displayed admissible alternative once or repeatedly
- raw rating evidence is durable, replayable, and independent of optimization availability

### Phase 3: add effective reducer and symmetric preference compiler

**Purpose:**
- translate low-friction ordinal evidence into one deterministic comparison algebra

**Primary targets:**
- `src/fitcv/decision_feedback.py`
- `tests/test_decision_feedback.py`

**Steps:**
1. define immutable `RatingValue`, effective-rating, preference-edge, diagnostic, and compiler-result records
2. reduce events by `(created_at, event_id)` through one shared query or reducer
3. validate episode, scale, feature contract, and profile compatibility before pairing
4. enumerate each unordered pair exactly once
5. orient qualifying pairs from higher rating to lower rating
6. omit unrated, equal, and below-gap pairs without inventing constraints
7. apply configured gap evidence weight
8. normalize total compiled edge weight within each episode
9. preserve source event IDs, compiler version, and deterministic edge ordering
10. fingerprint canonical compiler input and output

**Verification:**
- exhaustive table-driven tests cover every pair in `{unrated,1,2,3,4,5} x {unrated,1,2,3,4,5}`
- swapping input alternatives swaps edge orientation but preserves weight
- permuting input row order preserves canonical output and fingerprint
- compiling twice from same watermark produces byte-equivalent canonical output
- zero-edge episodes return valid `insufficient_evidence`

**Exit Criteria:**
- UI representation no longer matters after boundary adaptation
- every admissible rating case follows one reducer and one compiler path

### Phase 4: add CVXPY solver and episode-grouped evaluation

**Purpose:**
- infer bounded candidate weights using maintained optimization primitives

**Primary targets:**
- `pyproject.toml`
- `uv.lock`
- `src/fitcv/inverse_optimization.py`
- `scripts/run_inverse_optimization.py`
- `tests/test_inverse_optimization.py`

**Steps:**
1. add CVXPY and one validated QP solver only to offline dependency scope
2. adapt immutable compiler records to NumPy arrays inside solver boundary
3. build the declared regularized slack QP using CVXPY atoms and constraints
4. select solver and deterministic options from validated learning policy
5. map native solver statuses to owned typed result statuses
6. independently validate weight sum, bounds, finiteness, and preference residuals
7. persist immutable training-run input fingerprints, result, and diagnostics
8. split evaluation by episode using deterministic seeded grouping
9. compare candidate with exact parent snapshot on held-out evidence and stability gates
10. return diagnostics for rank deficiency and weak identification without deleting evidence
11. expose `train` and `evaluate` through one `argparse` script

**Verification:**
- synthetic recoverable case moves weights toward known preference direction
- contradictory case remains feasible through slack
- infeasible bounds fail before solver call
- row and edge permutations preserve result within configured numeric tolerance
- grouped evaluation never places edges from one episode in both train and validation
- runtime imports and baseline ranking work when offline solver extras are absent

**Exit Criteria:**
- training produces either a typed noncandidate result or one fully evidenced candidate result
- solver objects never cross application boundary

### Phase 5: add snapshot registry, activation, rollback, and runtime use

**Purpose:**
- promote learned policy safely without mutating past runs or baseline config

**Primary targets:**
- `src/fitcv_cp/store.py`
- `src/fitcv_cp/sqlite_store.py`
- `src/fitcv/pipeline.py`
- `src/fitcv/ranking.py`
- `scripts/run_inverse_optimization.py`
- `tests/test_pipeline.py`
- `tests/test_fitcv_cp/test_store.py`
- `tests/test_fitcv_cp/test_sqlite_store.py`

**Steps:**
1. persist candidate snapshots only after solver and evaluation gates pass
2. suppress candidate creation when weights equal parent within configured tolerance
3. add explicit reject, activate, and rollback commands
4. implement transactional compare-and-swap activation against current effective parent reference and current fingerprints
5. enforce one active compatible snapshot per domain, feature contract, and baseline policy fingerprint
6. append activation history for activate, reject, stale, retire, and rollback actions
7. resolve active snapshot once at run start
8. overlay learned weights onto baseline policy only after compatibility validation
9. record effective weights, snapshot ID, parent ID, and fingerprints in run settings and ranking artifact
10. fall back to baseline config on absent, incompatible, invalid, or unavailable snapshot storage

**Verification:**
- stale candidate cannot activate after baseline, learned parent, or evidence changes
- concurrent activation leaves one winner and one explicit conflict
- rollback creates auditable lifecycle transition and restores exact prior weights
- old runs retain original policy evidence after later activation
- failed activation leaves current active policy unchanged
- optimizer remains absent from runtime import graph

**Exit Criteria:**
- activation is manual and transactional
- every run is reproducible from persisted policy identity and artifact evidence

### Phase 6: add observability, reusable seam, docs, and deletion

**Purpose:**
- make behavior inspectable, document ownership, and remove superseded logic

**Primary targets:**
- `docs/architecture.md`
- `docs/configuration.md`
- `docs/pipeline.md`
- `docs/stages/ranking.source.yaml`
- `docs/features/cv_system/feature.source.yaml`
- affected tests and generated architecture outputs

**Steps:**
1. expose episode counts, effective-rating distribution, compiled-edge counts, skipped-case diagnostics, solver status, stability, staleness, and active snapshot identity
2. document canonical flow and source ownership without copying mutable config values
3. update human-owned feature and stage source files first
4. regenerate managed architecture outputs through canonical sync command
5. define a narrow domain-adapter record only when a second concrete decision domain is implemented
6. reuse ledger, reduction, compilation, optimization, evaluation, and lifecycle structures while keeping domain semantics and learned weights isolated
7. delete obsolete numeric defaults, shadow state, dead adapters, and temporary migration paths
8. record any retained simplification with a named ceiling and upgrade trigger

**Verification:**
- observability can explain why a rating did or did not create an edge
- docs point to canonical owners and generated outputs are synchronized
- deletion search finds no superseded production owner
- second-domain design demonstrates reuse without importing ranking-specific feature names into generic infrastructure

**Exit Criteria:**
- system is inspectable and source-first
- no speculative plugin framework exists
- implementation is ready for normal closeout workflow

## Design Decisions

### Decision: ordinal stars remain evidence SSOT

- context: stars are easy to provide but do not define cardinal utility distances
- choice: persist raw 1–5 labels and clear events; derive ordering only from configured clear gaps
- alternatives considered:
  - repeatedly ask explicit pairwise questions
  - convert stars directly into numeric utility targets
- impact:
  - user interaction stays low-friction
  - equal ratings and one-star gaps create no forced ordering in first policy

### Decision: one symmetric pair compiler handles all rating cases

- context: case-specific solver branches create drift and asymmetry
- choice: enumerate unordered pairs once, orient only qualifying unequal pairs, then emit one edge type
- alternatives considered:
  - separate rules for star combinations
  - transitive reduction before optimization
- impact:
  - all admissible cases share one algebra
  - permutation and swap properties become directly testable

### Decision: immutable artifact vectors freeze decision context

- context: recomputing old features under new code would rewrite historical evidence
- choice: copy exact feature vectors from ranking artifact into provenance-bound episode alternatives
- alternatives considered:
  - recompute from current job data
  - store only job ID and query current features
- impact:
  - training is replayable
  - feature-contract changes form separate cohorts

### Decision: configuration owns numeric policy; code owns semantics

- context: defaults currently drift across config, Python, settings, and tests
- choice: YAML owns mutable numeric values; code owns admissible names, types, direction, ranges, and validation
- alternatives considered:
  - hard-code all defaults
  - make config define executable feature semantics
- impact:
  - one numeric SSOT exists without turning config into code

### Decision: maintained convex solver stays offline

- context: project needs reliable inverse optimization, not a custom numerical library or runtime dependency
- choice: model QP in CVXPY with one explicit supported solver inside offline module
- alternatives considered:
  - hand-written optimizer
  - solver calls during ranking
- impact:
  - native solver behavior is reused
  - rating capture and runtime ranking remain available without solver stack

### Decision: evidence cohorts are compatibility-bound

- context: mixed feature contracts, profiles, or rating scales make one optimization problem semantically invalid
- choice: train only compatible cohorts and reject mixed inputs before matrix construction
- alternatives considered:
  - silently align missing dimensions
  - coerce old scales into current scale
- impact:
  - invalid cases fail uniformly at boundary
  - migration requires an explicit versioned adapter and new evidence fingerprint

### Decision: policy activation is separate from training

- context: optimization success alone does not prove business safety or freshness
- choice: create immutable candidates, evaluate them, then require manual transactional activation
- alternatives considered:
  - overwrite ranking config
  - auto-activate every optimal result
- impact:
  - active policy remains stable on failure
  - rollback and audit remain exact

### Decision: counts gate work but do not prove identification

- context: many correlated edges may still provide little independent feature information
- choice: use episode counts as prerequisites and require rank, conditioning, held-out, and resample diagnostics
- alternatives considered:
  - activate after a fixed edge count
- impact:
  - partially identified candidates remain visible but cannot pass stability gates accidentally

### Decision: native behavior is adapted once at boundaries

- context: custom form, persistence, serialization, CLI, and solver abstractions would duplicate maintained behavior
- choice: use browser forms, FastAPI parsing, SQLite constraints/transactions, standard-library records/JSON/hashing/CLI, and CVXPY primitives; convert data once at each boundary
- alternatives considered:
  - custom UI state framework
  - ORM and migration framework
  - custom matrix/problem DSL
  - CLI framework
- impact:
  - smaller implementation surface
  - native constraints remain authoritative and testable

### Decision: generic extension waits for second domain

- context: ranking is first concrete inverse-optimization domain
- choice: keep ranking adapter concrete; extract shared domain protocol only when second domain proves common shape
- alternatives considered:
  - plugin framework before first implementation
- impact:
  - no speculative abstraction
  - stable records and lifecycle still provide a clear reuse seam

## Reuse Contract and Future Components

Reusable structure is:

`ImmutableContext -> AppendOnlyEvidence -> EffectiveState -> SymmetricRelations -> BoundedOptimization -> CandidateSnapshot -> GroupedEvaluation -> ActivationLedger`

Shared infrastructure may own IDs, canonical JSON, fingerprints, append-only event mechanics, deterministic reduction, pair enumeration, solver result envelopes, evaluation grouping, immutable snapshot lifecycle, compare-and-swap activation, rollback, and observability envelopes.

Each domain must separately own alternative identity rules, feature contract, evidence scale semantics, relation compiler policy, feasible set, objective meaning, evaluation gates, and active policy. Learned weights and evidence never cross domains.

Components that may reuse this structure:

- **application history:** append `application_status` events against stable job identity; never infer application from a rating
- **active-learning job selection:** choose which unrated jobs would reduce uncertainty most, while rating UI remains unchanged
- **counterfactual explanation:** show smallest feature or policy change needed to reverse one ranking relation
- **preference drift:** compare time-grouped candidate snapshots without rewriting old evidence
- **what-if simulator:** evaluate hypothetical weights or constraints without creating or activating a snapshot
- **uncertainty report:** expose weakly identified dimensions and evidence coverage
- **threshold or subweight calibration:** reuse lifecycle with a new domain-specific feasible set and evaluation contract
- **shortlist or retrieval tuning:** learn bounded policy from ratings while preserving retrieval-specific feature semantics
- **soft-filter calibration:** treat filter outcomes as alternatives or policy actions only after a dedicated evidence contract exists
- **synonym proposal ratings:** rate normalized skill or title proposals and learn proposal policy in an isolated domain
- **CV evidence or draft ratings:** learn evidence-selection or drafting preferences without sharing ranking weights
- **provider routing:** learn bounded routing policy from explicit outcome evidence
- **job-source allocation:** learn source budgets under source-specific constraints

A new component may reuse generic lifecycle code only when it supplies all domain-owned contracts and passes the same admissibility, determinism, replay, evaluation, staleness, and activation tests. Similar table shape alone is not enough reason to share semantics.

## Invariants

1. Raw rating events are append-only user-evidence SSOT.
2. Effective ratings are derived; no mutable current-rating shadow owner exists.
3. Unrated means unknown, not neutral, zero, disliked, or missing-at-random.
4. Equal ratings create no equality or preference constraint.
5. Only rating gaps meeting versioned policy create one directed edge.
6. Swapping alternatives reverses edge direction and preserves edge weight.
7. Input ordering cannot change canonical edge set, fingerprints, solver problem, or policy result beyond declared numeric tolerance.
8. Every compiled edge is traceable to one episode and exact source rating events.
9. Episode alternatives use stable `raw_job_fingerprint`; mutable URLs never become primary identity.
10. Historical feature vectors come from immutable ranking artifacts and are never recomputed in place.
11. One episode and one training cohort contain one compatible domain, rating scale, profile context, and feature contract.
12. Baseline numeric ranking policy exists only in `config/policy/ranking.yaml`.
13. Decision-learning numeric policy exists only in `config/policy/decision_learning.yaml`.
14. Code owns feature semantics and admissible schemas; config cannot define executable feature logic.
15. Solver receives only validated finite vectors, feasible bounds, positive regularization, and canonical edge order.
16. Contradictory admissible evidence remains feasible through nonnegative slack.
17. Training never mutates baseline config or active policy.
18. Candidate snapshots are immutable and reference exact baseline, effective parent, evidence, compiler, optimizer, solver, and evaluation fingerprints.
19. Activation and rollback are transactional, compare-and-swap operations with append-only history.
20. At most one compatible active snapshot exists per domain, feature contract, and baseline policy fingerprint.
21. Old runs retain exact effective policy identity and ranking evidence after future activations.
22. Runtime ranking never imports or invokes CVXPY or offline solver packages.
23. Missing, incompatible, invalid, or unavailable learned policy falls back visibly to validated baseline config.
24. Application history and rating history are separate facts; neither is inferred from the other.
25. Shared infrastructure never shares domain evidence, semantic weights, or activation authority across domains.
26. Generated documentation is updated from human-owned sources, never hand-edited as authority.

## Acceptance Criteria

- one ownership table maps every canonical and derived fact to one owner
- one admissibility contract separates valid empty evidence, valid learnable evidence, and invalid input
- 1–5-star interactions persist exact ordinal events and support clear without JavaScript
- exhaustive rating-pair tests prove uniform compiler behavior
- property tests prove swap symmetry, permutation invariance, deterministic replay, and bounded episode influence
- solver tests prove feasibility with contradiction, pre-solver rejection of invalid policy, and independent residual validation
- evaluation tests prove episode-group separation and exact parent comparison
- snapshot tests prove immutability, baseline-parent compatibility, no-op suppression, staleness, one-active enforcement, concurrent activation safety, and rollback
- runtime tests prove baseline fallback and absence of offline solver imports
- store-boundary and SQLite tests prove no owned production path silently loses evidence or lifecycle events
- docs and config reference canonical owners rather than copied mutable values
- no implementation phase begins before its child spec is approved

## Non-Goals

- reconstruct past applications, ratings, or preferences that were never recorded
- infer an application from viewing, rating, shortlisting, or ranking a job
- replace 1–5 stars with repeated mandatory pairwise questions
- treat ordinal stars as cardinal utility values
- learn from equal ratings or below-gap ratings in first implementation
- optimize thresholds, subweights, filters, retrieval, providers, or source allocation in ranking-v1 solver
- personalize per session, device, or anonymous viewer
- mix users, profiles, feature contracts, rating scales, or domains in one cohort
- auto-activate learned policy
- call optimizer in request handling or runtime ranking
- add an ORM, migration framework, UI state framework, custom optimizer, matrix DSL, CLI framework, event bus, or plugin framework
- backfill mutable features into historical episodes
- expose private operating-system artifacts through public mirror

## Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| duplicated numeric defaults survive | inventory and search gate in Phase 1; delete competing production owners |
| rating semantics drift | version scale and compiler policy; retain raw events |
| pair explosion within large episodes | top reviewed set is bounded; compiler uses deterministic combinations; add materialized-edge cache only after measured need |
| one episode dominates through many pairs | normalize total edge weight per episode |
| edge correlation inflates evaluation | split and resample by episode, never edge |
| weak identifiability looks like confidence | require rank, conditioning, resample, and held-out diagnostics |
| contradictory evidence makes hard constraints fail | use nonnegative slack and retain contradiction diagnostics |
| mutable URLs split identity | use `raw_job_fingerprint` first; URL remains metadata |
| old features drift under new code | freeze artifact vectors and contract fingerprints |
| stale candidate overwrites newer truth | transactional parent and fingerprint compare-and-swap |
| solver package breaks runtime | offline module and dependency boundary; runtime import test |
| persistence outage creates hidden state | baseline fallback; no memory-only active policy |
| future backend silently omits feedback | explicit unsupported error until contract tests exist |
| generic abstraction leaks ranking semantics | delay shared protocol until second concrete domain |
| generated docs drift | edit source YAML first; run architecture sync check |
| ratings mistaken for application history | separate ledgers and UI labels; never infer either fact |

## Validation Plan

- proof target: planning artifact follows repo lifecycle
  - method: run `python scripts/validate_planning_lifecycle.py`
  - evidence: this spec passes required frontmatter, section, parent-thread, and target validation
- proof target: generated planning lineage includes this spec
  - method: run `python scripts/generate_planning_lineage.py`
  - evidence: `docs/generated/planning_lineage.yaml` is regenerated from current thread/spec metadata
- proof target: architecture documentation stays source-first
  - method: update human-owned source YAML, run `python tools/docs/generate_architecture_metadata.py`, then `python tools/docs/generate_architecture_metadata.py --check`
  - evidence: generated feature, stage, lineage, and discovery outputs match sources
- proof target: repo contracts remain valid
  - method: run `python scripts/validate_repo_contracts.py`
  - evidence: canonical repo-wide validator passes
- proof target: baseline ranking behavior remains stable after SSOT consolidation
  - method: run focused ranking and pipeline tests with canonical baseline config
  - evidence: pre-change fixtures and final score ordering remain unchanged where policy values are unchanged
- proof target: rating persistence is append-only and replayable
  - method: store-boundary, SQLite, and HTTP tests for set, change, clear, invalid input, and atomic first write
  - evidence: event sequence deterministically reduces to expected effective state with no update-in-place path
- proof target: compiler is uniform and symmetric
  - method: exhaustive 36-state pair matrix plus swap, permutation, and repeatability tests
  - evidence: only configured clear gaps emit one correctly oriented, deterministically weighted edge
- proof target: optimization is bounded and independently checked
  - method: synthetic, contradictory, rank-deficient, infeasible-policy, and solver-failure tests
  - evidence: typed status, finite weights, simplex residual, bound residual, and preference residual match contract
- proof target: evaluation has no episode leakage
  - method: inspect deterministic grouped split membership in tests
  - evidence: one episode ID appears in exactly one partition per evaluation fold
- proof target: lifecycle prevents unsafe promotion
  - method: candidate, no-op, stale, concurrent activation, rejection, rollback, and failed-transaction tests
  - evidence: one active snapshot remains and activation ledger explains every transition
- proof target: runtime stays solver-independent and reproducible
  - method: import/runtime tests without offline extras plus persisted artifact assertions
  - evidence: baseline or compatible active weights rank normally; run records exact policy identity
- proof target: superseded truth is deleted
  - method: source search for removed fallback dictionaries, copied defaults, mutable current-rating fields, and alternate active-policy registries
  - evidence: only canonical owners remain

Implementation child plans should start with focused tests, then broaden to:

```text
python -m pytest tests/test_decision_feedback.py
python -m pytest tests/test_inverse_optimization.py
python -m pytest tests/test_ranking.py tests/test_ai_score.py tests/test_pipeline.py
python -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_sqlite_store.py
python scripts/generate_planning_lineage.py
python tools/docs/generate_architecture_metadata.py --check
python scripts/validate_planning_lifecycle.py
python scripts/validate_repo_contracts.py
```

Exact solver installation and optional-dependency test commands belong to Phase 4 child spec after solver selection is verified against supported Python and CI platforms.

## Completion Criteria

This master specification is complete when:

1. all required sections and ownership decisions are present
2. the admissible-case matrix covers empty, ambiguous, contradictory, incompatible, failure, concurrency, staleness, rollback, and historical-replay cases
3. each phase names purpose, ordered steps, verification, and exit criteria
4. required child specs are named and sequenced
5. plan-document review returns `ready` after blocking findings are fixed
6. planning lifecycle, architecture check, and repo-contract validators pass
7. master spec is approved for child-spec drafting

Inverse-optimization implementation is complete only when:

1. all six child specs are approved
2. all child implementation plans are completed or explicitly dropped
3. every invariant has cited verification evidence
4. obsolete duplicate owners are deleted
5. active policy lifecycle passes concurrency, staleness, rollback, and reproducibility checks
6. feature and stage source docs plus generated outputs are synchronized
7. closeout follows canonical repo workflow

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `docs/operating_system/lifecycle/doc-system-lifecycle.md`
- `docs/operating_system/templates/detailed-specification-template.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>