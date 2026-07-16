---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: fitcv-inverse-optimization-phase-7-policy-lifecycle-runtime-residual-closeout
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-stage-authority-contract
parent_spec: docs/superpowers/specs/2026-07-14-22-25-fitcv-inverse-optimization-master-ssot-symmetry-spec.md
targets:
  - config/policy/decision_learning.yaml
  - src/fitcv/preference_policy.py
  - src/fitcv/inverse_optimization.py
  - src/fitcv/ranking.py
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_runner.py
  - src/fitcv/pipeline_stage_artifacts.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv_cp/store.py
  - src/fitcv_cp/sqlite_store.py
  - scripts/run_inverse_optimization.py
  - tests/test_config.py
  - tests/test_preference_policy.py
  - tests/test_inverse_optimization.py
  - tests/test_ranking.py
  - tests/test_pipeline.py
  - tests/test_pipeline_stage_resume_parity.py
  - tests/test_fitcv_cp/test_store.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - docs/architecture.md
  - docs/configuration.md
  - docs/pipeline.md
  - docs/stages/ranking.source.yaml
  - docs/stages/cv_analysis.source.yaml
  - docs/features/cv_system/feature.source.yaml
related_features:
  - cv_system
  - admin_control_plane_core
  - inspection_debugging
  - settings_system
related_stages:
  - ranking
  - cv_analysis
---

# Detailed Spec: FitCV inverse optimization Phase 7 policy lifecycle, runtime residual, observability, and closeout

## Goal

Promote one compatible Phase 6 latent preference vector through an immutable,
transactional, reversible policy lifecycle, apply it once per run through a
solver-free runtime boundary, preserve baseline labels and CV gates, expose all
evidence needed to explain behavior, and remove superseded ranking-learning
truth.

```text
Phase 6 solver result + grouped evaluation + current immutable evidence
-> immutable training-run record
-> optional immutable candidate snapshot
-> manual compare-and-swap lifecycle transition
-> one run-scoped resolved preference policy
-> baseline score + bounded latent residual
-> raw personalized ordering + clipped display projection
-> unchanged baseline label and downstream CV gate
```

Phase 7 is final implementation phase in master specification. Phases 1–6 are
complete. No Phase 8 exists in current master scope.

Phase 7 does not learn baseline weights, reinterpret star ratings, call solver
during production ranking, add BM25/BM25F, infer application history, or create
generic multi-domain policy framework.

## Triage

- layer: `change`
- feature type: `ADD` plus bounded `DELETE`
- parent: inverse-optimization master SSOT and symmetry specification
- dependencies: completed Phases 1–6
- primary stages: `ranking`, then `cv_analysis` as baseline-label consumer
- primary feature: `cv_system`
- supporting features: control-plane storage, diagnostics, configuration
- implementation code: out of scope for this document
- implementation plan: required after approval
- generated refresh required during implementation: yes
- GitNexus: index predates Phase 6 commit; source and tests remain authoritative

## Current-State Diagnosis

Completed reusable owners:

- `config/policy/ranking.yaml` owns fixed baseline numeric policy
- `config/policy/decision_learning.yaml` owns rating, compiler, optimizer,
  solver, numeric tolerance, and evaluation numeric policy
- `src/fitcv/ranking_contract.py` owns `baseline_fit` and
  `baseline_fit_label`
- `src/fitcv/ranking.py::rank_jobs(...)` owns canonical baseline ordering and
  `baseline_rank`
- decision episodes, alternatives, and rating events own immutable evidence
- `compile_preference_edges(...)` owns deterministic preference relations
- `solve_preference_residual(...)` and `evaluate_preference_residual(...)` own
  offline solver and grouped evaluation behavior
- `src/fitcv_cp/sqlite_store.py` owns native SQLite transactions

Missing final boundary:

- solver-free immutable policy payload schema
- training-run and policy-lifecycle persistence
- candidate promotion gate and no-op suppression
- reject, activate, rollback, and inspection commands
- run-scoped active-policy resolution and visible zero-residual fallback
- raw personalized ordering without relabeling
- policy/runtime diagnostics, replay evidence, docs, and deletion proof

`src/fitcv/inverse_optimization.py` remains offline solver code. Runtime ranking
must not import it. One small solver-free module,
`src/fitcv/preference_policy.py`, owns policy records, validation,
compatibility, lifecycle result types, and standard-library residual math.

## Key Deliverables

### Deliverable 1: one solver-free preference-policy contract

Add `src/fitcv/preference_policy.py` with frozen plain-Python records only. It
must not import CVXPY, CLARABEL, NumPy, FastAPI, or SQLite.

Canonical records:

```text
PreferenceRuntimeContract
  schema_version: preference_runtime_contract_v1
  domain_id
  baseline_policy_fingerprint
  ranking_contract_fingerprint
  embedding_model
  embedding_dimension
  embedding_contract_fingerprint
  learned_alpha
  preference_vector_norm_bound
  runtime_contract_fingerprint

RankingPolicySnapshot
  schema_version: ranking_policy_snapshot_v1
  policy_snapshot_id
  domain_id
  status: candidate | active | rejected | stale | retired
  runtime_contract
  parent_policy_kind: zero_residual | learned
  parent_policy_ref
  preference_vector
  preference_vector_fingerprint
  payload_fingerprint
  training_run_id
  event_watermark
  cohort_fingerprint
  edge_set_fingerprint
  rating_scale_version
  compiler_version
  compiler_policy_fingerprint
  decision_learning_policy_fingerprint
  optimizer_policy_fingerprint
  activation_policy_fingerprint
  problem_fingerprint
  solver_name
  solver_version
  solver_options_fingerprint
  evaluation_version
  evaluation_fingerprint
  solver_metadata
  evaluation
  created_at
  activated_at

ResolvedPreferencePolicy
  schema_version: resolved_preference_policy_v1
  resolution_status:
    active
    zero_residual_no_active
    zero_residual_incompatible
    zero_residual_invalid
    zero_residual_unavailable
  runtime_contract
  policy_snapshot_id
  preference_vector
  preference_vector_fingerprint
  payload_fingerprint
  diagnostic_code

PersonalizedScoreProjection
  baseline_fit
  preference_residual
  personalized_rank_score
  personalized_display_score
  score_was_clipped
```

`runtime_contract_fingerprint` hashes normalized runtime fields above. It
excludes compiler, optimizer, solver, and evaluation provenance. Training-tool
changes may stale candidate but cannot disable runtime-compatible active vector.

`payload_fingerprint` hashes canonical immutable snapshot content, excluding
`policy_snapshot_id`, `status`, `activated_at`, and storage timestamps.
Snapshot identity is content-addressed:

```text
policy_snapshot_id = "rps_" + payload_fingerprint
```

`training_run_id` is likewise derived from the canonical terminal-attempt
payload/result fingerprint, excluding its ID and storage timestamp. Exact retry
returns the existing immutable row. No timestamp, row count, random UUID, or
operator identity participates in either content identity.

Canonical runtime equations:

```text
dot = math.fsum(
  preference_vector[i] * normalized_embedding[i]
  for i in range(embedding_dimension)
)
preference_residual = learned_alpha * dot
personalized_rank_score = baseline_fit + preference_residual
personalized_display_score = min(1.0, max(0.0, personalized_rank_score))
score_was_clipped = personalized_rank_score < 0.0 or personalized_rank_score > 1.0
```

Validation rejects unknown schema/status/parent kind, empty identity, non-finite
numeric values, nonpositive dimension, vector/embedding mismatch, invalid
alpha, over-bound norm, non-normalized embedding, or fingerprint mismatch.

Zero-residual resolution uses no synthetic persisted snapshot. It returns zero
residual, null snapshot ID, and visible status.

### Deliverable 2: one exact activation-policy extension

Extend existing `decision_learning_policy.inverse_optimization` block:

```yaml
activation:
  activation_version: ranking-policy-lifecycle-v1
  minimum_fold_vector_stability: 0.0
```

Rules:

- existing `numeric_equivalence_absolute` owns candidate equivalence and metric
  comparison tolerance
- `minimum_fold_vector_stability` is finite in `[-1, 1]`
- no CLI override and no admin setting exist
- code owns gate semantics; config owns mutable numeric threshold
- `activation_policy_fingerprint` hashes normalized activation block
- active runtime compatibility excludes activation fingerprint

Uniform promotion gate requires optimal independently validated vector,
evaluated complete folds, aggregate candidate metrics, configured minimum fold
stability, no regression beyond tolerance on pair agreement, margin
satisfaction, weighted regret, and clipping frequency, plus strict improvement
on at least one decision metric. Same comparison applies against zero baseline
and compatible learned parent. Rank-change fraction, coverage, and unavailable
retrieval recall remain diagnostics.

For Phase 7, clipping comparison is intentionally strict: zero-residual baseline
has zero clipping, therefore an activatable candidate must also have zero
held-out clipping. Runtime still records clipping for fallback, diagnostics, and
future policy review; Phase 7 adds no second clipping threshold.

Metric direction is fixed:

```text
higher is better: pair_agreement_rate, margin_satisfaction_rate
lower is better: weighted_regret, clipping_frequency
diagnostic only: rank_change_fraction
```

Missing required metric fails gate. Training evidence persists; candidate does
not.

### Deliverable 3: native SQLite persistence with immutable payloads

Extend `src/fitcv_cp/sqlite_store.py` through one
`_ensure_local_preference_policy_tables(...)` owner. Reuse `sqlite3`, JSON,
transactions, checks, foreign keys, indexes, and timestamps. Add no ORM or
migration framework.

#### `inverse_training_runs`

Required columns:

```text
training_run_id TEXT PRIMARY KEY
schema_version TEXT NOT NULL
domain_id TEXT NOT NULL
status TEXT NOT NULL
cohort_fingerprint TEXT NOT NULL
event_watermark INTEGER NOT NULL CHECK event_watermark >= 0
edge_set_fingerprint TEXT NOT NULL
rating_scale_version TEXT NOT NULL
compiler_version TEXT NOT NULL
compiler_policy_fingerprint TEXT NOT NULL
decision_learning_policy_fingerprint TEXT NOT NULL
optimizer_policy_fingerprint TEXT NOT NULL
activation_policy_fingerprint TEXT NOT NULL
baseline_policy_fingerprint TEXT NOT NULL
ranking_contract_fingerprint TEXT NOT NULL
embedding_model TEXT NOT NULL
embedding_contract_fingerprint TEXT NOT NULL
embedding_dimension INTEGER NOT NULL CHECK embedding_dimension > 0
learned_alpha REAL NOT NULL
parent_policy_kind TEXT NOT NULL CHECK parent_policy_kind IN ('zero_residual', 'learned')
parent_policy_ref TEXT NOT NULL
problem_fingerprint TEXT
evaluation_fingerprint TEXT
result_json TEXT NOT NULL
created_at TEXT NOT NULL
```

Training-run status:

```text
candidate_created
no_op
evaluation_rejected
insufficient_evidence
invalid_input
infeasible_policy
solver_error
```

Every terminal candidate attempt persists one immutable training row.
`result_json` is canonical JSON containing solver result, evaluation result,
promotion-gate result, no-op comparison, and diagnostics. Lifecycle operations
never update or delete training rows.

#### `ranking_policy_snapshots`

Required columns:

```text
policy_snapshot_id TEXT PRIMARY KEY
schema_version TEXT NOT NULL
domain_id TEXT NOT NULL
status TEXT NOT NULL CHECK status IN ('candidate', 'active', 'rejected', 'stale', 'retired')
runtime_contract_fingerprint TEXT NOT NULL
baseline_policy_fingerprint TEXT NOT NULL
ranking_contract_fingerprint TEXT NOT NULL
embedding_model TEXT NOT NULL
embedding_contract_fingerprint TEXT NOT NULL
embedding_dimension INTEGER NOT NULL CHECK embedding_dimension > 0
learned_alpha REAL NOT NULL
preference_vector_norm_bound REAL NOT NULL
parent_policy_kind TEXT NOT NULL CHECK parent_policy_kind IN ('zero_residual', 'learned')
parent_policy_ref TEXT NOT NULL
preference_vector_json TEXT NOT NULL
preference_vector_fingerprint TEXT NOT NULL
payload_fingerprint TEXT NOT NULL UNIQUE
training_run_id TEXT NOT NULL REFERENCES inverse_training_runs(training_run_id)
event_watermark INTEGER NOT NULL CHECK event_watermark >= 0
cohort_fingerprint TEXT NOT NULL
edge_set_fingerprint TEXT NOT NULL
rating_scale_version TEXT NOT NULL
compiler_version TEXT NOT NULL
compiler_policy_fingerprint TEXT NOT NULL
decision_learning_policy_fingerprint TEXT NOT NULL
optimizer_policy_fingerprint TEXT NOT NULL
activation_policy_fingerprint TEXT NOT NULL
problem_fingerprint TEXT NOT NULL
solver_metadata_json TEXT NOT NULL
evaluation_version TEXT NOT NULL
evaluation_fingerprint TEXT NOT NULL
evaluation_json TEXT NOT NULL
created_at TEXT NOT NULL
activated_at TEXT
```

Native enforcement:

- partial unique index on `(domain_id, runtime_contract_fingerprint)` where
  `status = 'active'`
- immutable-payload trigger rejects update to every column except `status` and
  `activated_at`
- no generic snapshot-update function
- store-owned lifecycle functions are the only supported application mutation
  path and update status plus ledger in one transaction
- frozen solver/evaluation copies must fingerprint-match referenced training row
- snapshots are never deleted; lifecycle state explains supersession

#### `policy_activation_events`

Required columns:

```text
activation_event_id TEXT PRIMARY KEY
domain_id TEXT NOT NULL
runtime_contract_fingerprint TEXT NOT NULL
previous_snapshot_id TEXT
target_snapshot_id TEXT
action TEXT NOT NULL CHECK action IN ('activate', 'reject', 'stale', 'retire', 'rollback')
reason_code TEXT NOT NULL
expected_parent_ref TEXT
evidence_head_fingerprint TEXT
acted_by TEXT NOT NULL
created_at TEXT NOT NULL
```

Ledger is append-only and sole lifecycle history. Snapshot `status` is its
transactionally maintained current-state projection, not a second history or
registry. Tests must prove projection and reduced ledger agree after every
supported lifecycle operation. SQLite directly enforces payload immutability,
status enum, foreign keys, and one-active uniqueness; store tests enforce legal
transition plus event coupling.

Store protocol adds typed methods:

```text
persist_inverse_training_result
insert_ranking_policy_candidate
reject_ranking_policy_candidate
activate_ranking_policy_candidate
rollback_ranking_policy
resolve_active_ranking_policy
inspect_ranking_policy_lifecycle
```

`ControlPlaneStore` remains boundary adapter. SQLite remains canonical local
owner.

### Deliverable 4: candidate creation, evidence head, and no-op suppression

Candidate creation is manual offline operation. It uses Phase 6 full-refit and
evaluation outputs plus current decision-learning policy and current effective
parent.

Canonical parent reference:

```text
no compatible active snapshot:
  parent_policy_kind = zero_residual
  parent_policy_ref = zero_residual:<baseline_policy_fingerprint>
  comparator_vector = all zeros

compatible active snapshot:
  parent_policy_kind = learned
  parent_policy_ref = learned:<policy_snapshot_id>
  comparator_vector = exact active preference vector
```

Current evidence head is rebuilt from persisted decision episodes,
alternatives, and all rating events for one exact compatible cohort from one
short SQLite snapshot transaction. It contains:

```text
domain_id
sorted compatible episode identities
current event watermark
per-episode compiler_input_fingerprint
per-episode edge_set_fingerprint
cohort_fingerprint
aggregate edge_set_fingerprint
evidence_head_fingerprint
```

Candidate input must match current evidence head. File-only `train` and
`evaluate` remain pure commands, but only store-verified evidence may create
persistent candidate.

No-op comparison reuses numeric-equivalence tolerance:

```text
max_coordinate_delta = max(
  abs(candidate_preference_vector[i] - comparator_vector[i])
)
no_op = max_coordinate_delta <= numeric_equivalence_absolute
```

Empty vector, dimension mismatch, or non-finite value fails validation; it never
becomes no-op silently.

Candidate operation order:

1. load and validate current policy
2. resolve current compatible parent
3. load current compatible evidence plus parent/head CAS tokens under one short
   store transaction, then commit
4. solve and evaluate outside the database transaction
5. apply uniform promotion gate
6. open one short write transaction and recheck current evidence, parent, config,
   and runtime CAS tokens
7. persist immutable training-run row for every terminal result; changed tokens
   produce `invalid_input` with `stale_evidence`
8. stop with no snapshot on noncandidate, stale evidence, or no-op
9. build and insert immutable candidate payload on passing non-no-op result, then
   commit

Candidate and training IDs use the content-addressed definitions above. Exact
retry returns existing matching immutable record instead of duplicate churn.
Conflicting same ID fails.

### Deliverable 5: transactional lifecycle and compare-and-swap semantics

All lifecycle writes use `BEGIN IMMEDIATE`, validate before mutation, append
events before commit, and rollback on any exception.

#### Reject

Allowed transition:

```text
candidate -> rejected
```

Reject requires candidate ID, expected candidate status, nonempty `acted_by`,
and reason. It appends one `reject` event. Exact retry returns terminal state
without second event. Conflicting reason never rewrites history.

#### Activate

Activate requires candidate ID, caller-inspected expected parent reference,
current runtime contract fingerprint, current evidence-head fingerprint, and
nonempty `acted_by`.

Transaction:

1. load candidate and verify `candidate`
2. load current effective parent for candidate runtime contract
3. compare caller expected parent, candidate parent, and current parent
4. re-read cheap current config/runtime/evidence CAS tokens inside transaction;
   expensive compiler reconstruction occurred before the transaction
5. if training or evidence contract changed, mark candidate `stale`, append
   `stale`, commit, and return stale result
6. if parent changed because another activation won, mark loser `stale`, append
   `stale` with `parent_changed`, commit, and return explicit conflict
7. if previous active exists, mark it `retired` and append `retire`
8. mark candidate `active`, set `activated_at`, and append `activate`
9. commit

Partial unique index is final one-active guard.

#### Rollback

Rollback requires expected current active snapshot ID and target:

- one previously `retired` snapshot with same runtime contract, or
- `zero_residual:<baseline_policy_fingerprint>`

Transaction:

1. verify current active matches expected ID
2. verify target runtime compatibility and immutable payload validity
3. retire current active and append `retire`
4. for learned target, change target `retired -> active`, refresh
   `activated_at`, and append `rollback`
5. for zero target, leave no active snapshot and append `rollback` with null
   target snapshot ID
6. commit

Rollback never reruns solver or rewrites target vector. Concurrent rollback or
activation produces one winner and one explicit conflict.

Direct transitions not listed above are invalid. `stale`, `rejected`, and
current `active` snapshots cannot be activation targets. `retired` can return to
`active` only through rollback.

### Deliverable 6: resolve once, rank by raw score, preserve labels

Pipeline resolves one `ResolvedPreferencePolicy` after validated ranking and
embedding contracts are known and before ranking rows are ordered. Resolution
occurs once per run, then exact resolved payload is stored in run/checkpoint
state. Resume reuses stored payload and never resolves newer activation.

Resolver is injected once at the pipeline orchestrator boundary as one callable
from `PreferenceRuntimeContract` to `ResolvedPreferencePolicy`. Worker and CLI
entrypoints adapt the same `ControlPlaneStore` method into that callable. Tests
may inject the canonical zero-residual resolver. Core ranking code never imports
`fitcv_cp` or opens the policy database directly.

Resolver behavior:

| Case | Run-scoped result | Ranking effect |
|---|---|---|
| one valid compatible active snapshot | `active` | apply exact vector |
| no active snapshot | `zero_residual_no_active` | baseline order |
| only incompatible active snapshots | `zero_residual_incompatible` | baseline order plus diagnostic |
| active payload fails validation | `zero_residual_invalid` | baseline order plus diagnostic |
| SQLite unavailable or unreadable | `zero_residual_unavailable` | baseline order plus diagnostic |

Resolver never chooses nearest contract, latest incompatible payload, or
candidate snapshot. Multiple compatible active rows are corruption and produce
visible invalid fallback, though unique index should prevent them.

Ranking order advances ranking-order semantics to
`baseline-all-eligible-personalized-fingerprint-url-v1`. Old ranking-v2 rows and
checkpoints remain readable through the existing boundary adapter.

Ranking order:

1. compute canonical baseline rows exactly as Phase 3
2. assign deterministic `baseline_rank` across all scored eligible rows using
   current baseline tie-breakers
3. compute personalized projection for every scored eligible row
4. sort by descending `personalized_rank_score`
5. preserve tie-breakers `raw_job_fingerprint`, then `job_url`
6. assign `personalized_rank`
7. apply `top_n` after personalized ordering

Required row fields:

```text
baseline_fit
baseline_fit_label
baseline_rank
preference_residual
personalized_rank_score
personalized_display_score
score_was_clipped
personalized_rank
preference_policy_snapshot_id
preference_vector_fingerprint
preference_runtime_contract_fingerprint
baseline_policy_fingerprint
ranking_contract_fingerprint
embedding_contract_fingerprint
embedding_vector_fingerprint
policy_resolution_status
```

`baseline_fit`, `baseline_fit_label`, and `baseline_rank` remain baseline facts.
Legacy aliases continue projecting baseline facts only. No existing `final_*`
alias silently changes meaning to personalized score.

Downstream contract:

- `strong | stretch | skip` derives only from persisted `baseline_fit_label`
- fallback label derivation may use `baseline_fit` only
- CV analysis and generation gates ignore personalized score and rank
- learned residual changes ordering only
- jobs introduced into top N by personalized order retain baseline rank/label
- score clipping affects display only, never ordering or pair evaluation

Runtime modules import neither CVXPY nor NumPy solely for dot product.

### Deliverable 7: run replay and observability without shadow state

Ranking stage artifact adds one bounded `personalization` block:

```text
schema_version: ranking_personalization_v1
resolution_status
diagnostic_code
runtime_contract_fingerprint
policy_snapshot_id
payload_fingerprint
preference_vector
preference_vector_fingerprint
learned_alpha
preference_vector_norm_bound
residual_min
residual_max
residual_mean
clipped_count
clipped_rate
rank_change_count
rank_change_rate
```

Full resolved vector is stored once in run artifact, not every job row. Rows
reference snapshot/vector fingerprints. Old-run replay remains exact after
later activation, retirement, rollback, solver change, or DB unavailability.

`inspect` composes existing SSOTs; it creates no diagnostics table:

- factor and eligibility diagnostics from ranking/run artifacts
- retrieval audit from Phase 2/6 artifacts
- rating counts and watermarks from rating-ledger reduction
- edge counts, omissions, budgets, and fingerprints from compiler
- solver status/version/options, norm, violation, and timing from training run
- evaluation coverage, stability, clipping, regret, and rank change
- candidate status, staleness reason, parent, and payload identity
- current active payload and runtime compatibility
- activation ledger transitions

`inspect --domain <id>` returns lifecycle/training evidence. Optional
`--run-id <id>` adds factor, eligibility, retrieval, and run personalization.
Missing evidence stays `not_available`; no zero or success value is fabricated.

### Deliverable 8: one standard-library CLI lifecycle surface

Extend `scripts/run_inverse_optimization.py` existing `argparse` CLI. Keep
canonical JSON, atomic output replacement, and no HTTP dependency.

```text
train --domain <id> --input <bundle.json> [--output <path>]
evaluate --domain <id> --input <bundle.json> [--parent <path>] [--output <path>]
candidate --domain <id> --input <bundle.json> [--output <path>]
reject --snapshot <id> --acted-by <text> --reason <text> [--output <path>]
activate --snapshot <id> --expected-parent <ref> --acted-by <text> [--output <path>]
rollback --domain <id> --expected-active <id> --target <id|zero_residual> --acted-by <text> [--output <path>]
inspect --domain <id> [--run-id <id>] [--output <path>]
```

Lifecycle commands use configured local SQLite store. `train` and `evaluate`
stay pure file commands. Candidate verifies input bundle against current
persisted evidence before insertion.
Stale or foreign candidate input is the `invalid_input` training status with
diagnostic code `stale_evidence`.

Exit codes:

```text
0: valid terminal result or completed lifecycle action
2: invalid input or unknown identifier
3: solver/dependency/storage failure
4: promotion rejected, stale candidate, incompatible target, invalid state, or compare-and-swap conflict
```

Every command emits typed JSON. No command prints secret config, credentials,
full job text, or mutable object representation.

### Deliverable 9: source-first docs and bounded deletion closeout

Update human-owned sources first:

- `docs/stages/ranking.source.yaml`: runtime personalized ordering, score
  projection, and fallback diagnostics; baseline label unchanged
- `docs/stages/cv_analysis.source.yaml`: CV analysis consumes baseline label only
- `docs/features/cv_system/feature.source.yaml`: replace Phase 6 no-activation
  wording with active lifecycle/runtime capability
- `docs/architecture.md`: payload, transaction, resolver, runtime math, fallback,
  replay, and ownership
- `docs/configuration.md`: activation block, validation, commands, no override
- `docs/pipeline.md`: resolve-once flow, score fields, top-N, resume, label
  invariance

Then regenerate managed stage/feature/architecture/planning outputs. Never edit
generated YAML or generated history as authority.

Deletion inventory:

- remove obsolete text claiming preference learning cannot persist, activate, or
  affect runtime ordering after Phase 7
- remove remaining active shortlist BM25/BM25F config, settings, code, tests,
  docs, or adapters; historical specs may retain history
- retain unrelated lexical evidence inside CV-analysis semantic alignment
- remove learned-baseline-weight names/defaults/fields/docs if any remain
- remove parallel active-policy registries, mutable current-rating state, and
  temporary candidate adapters
- remove `store_final_ranking` no-op hook and injection plumbing after impact
  proof confirms no active persistence consumer
- retain no compatibility shim without current caller and removal reason

Do not create generic policy-domain plugin/adapter framework. Extract shared
domain abstraction only after second concrete decision domain proves same
contracts and lifecycle tests.

## Admissible-Case Matrix

| Case | Training persistence | Snapshot effect | Runtime effect | Diagnostic |
|---|---|---|---|---|
| no ratings | `insufficient_evidence` | none | current active or zero fallback | explicit counts |
| one rated alternative | `insufficient_evidence` | none | unchanged | explicit counts |
| equal or one-star gaps only | `insufficient_evidence` | none | unchanged | compiler omissions |
| clear-gap evidence, evaluation passes | `candidate_created` | one candidate | none until activation | full provenance |
| evaluation gate fails | `evaluation_rejected` | none | unchanged | failed metrics |
| vector equals zero within tolerance | `no_op` | none | unchanged | zero comparator |
| vector equals parent within tolerance | `no_op` | none | unchanged | parent comparator |
| contradictory evidence | terminal result | candidate only if gates pass | unchanged until activation | slack/violation |
| weak or reversed fold direction | `evaluation_rejected` | none | unchanged | stability failure |
| evidence changes before activation | retained row | candidate stale | unchanged | stale event |
| config/training provenance changes | retained row | candidate stale | unchanged | stale event |
| solver version changes after activation | no mutation | active stays if runtime-compatible | old vector used | provenance drift |
| concurrent activation | both audited | one active, loser stale | winner used next run | conflict |
| rollback to learned snapshot | no retraining | exact retired target active | prior vector | rollback event |
| rollback to zero residual | no retraining | no active snapshot | baseline order next run | rollback event |
| no active snapshot | none | none | zero residual | no-active status |
| incompatible active snapshot | none | no mutation | zero residual | incompatible status |
| corrupt active payload | none | no mutation | zero residual | invalid status |
| SQLite unavailable | none | no mutation | zero residual for full run | unavailable status |
| old run viewed after activation | no mutation | no mutation | stored payload reused | replay evidence |
| personalized order reverses jobs | no mutation | no mutation | raw order changes | labels unchanged |
| raw score outside `[0,1]` | no mutation | no mutation | raw orders, display clips | clipping flag |

Every case uses same payload validator, compatibility function, promotion
comparator, lifecycle transaction pattern, and runtime score projection. No
case-specific score formula exists.

## Task/Wave Breakdown

### Wave 1: freeze policy and lifecycle contracts

**Purpose:**
- establish solver-free records, fingerprints, gates, schema, and lifecycle
  algebra before ranking mutation

**Steps:**
- [ ] add failing tests for records, fingerprints, equations, invalid vectors,
  and fallback statuses
- [ ] extend activation policy and validation
- [ ] define training-run, snapshot, event, and lifecycle-result records
- [ ] define evidence-head and no-op comparison
- [ ] define promotion comparison over baseline and parent

**Verification:**
- [ ] one normalized value set produces one fingerprint set
- [ ] validation failures are typed before storage mutation
- [ ] runtime module imports no offline solver dependency

**Exit Criteria:**
- policy, payload, compatibility, and promotion semantics have no open choice

### Wave 2: persist immutable evidence and candidates

**Purpose:**
- reuse SQLite constraints/transactions for one canonical policy registry

**Steps:**
- [ ] add tables, checks, foreign keys, immutable trigger, and partial unique
  active index
- [ ] add typed store protocol and control-plane adapters
- [ ] persist every terminal training attempt exactly once
- [ ] verify current persisted evidence before candidate creation
- [ ] suppress zero/parent-equivalent candidate snapshots
- [ ] add retry, malformed JSON, corruption, and rollback tests

**Verification:**
- [ ] payload columns cannot mutate
- [ ] exact retry is idempotent
- [ ] failed transaction leaves no partial row or event

**Exit Criteria:**
- one DB authority owns training records, snapshots, active state, and history

### Wave 3: add lifecycle commands and inspection

**Purpose:**
- make promotion manual, compare-and-swap safe, auditable, and reversible

**Steps:**
- [ ] add reject transition
- [ ] add activation with parent/config/runtime/evidence checks
- [ ] add stale transition for changed evidence/provenance
- [ ] add learned and zero-residual rollback
- [ ] add concurrent-operation tests using separate SQLite connections
- [ ] extend CLI and exit-code contract
- [ ] compose diagnostics from existing owners

**Verification:**
- [ ] concurrent activation yields one winner and explicit conflict
- [ ] rollback restores byte-equivalent prior vector payload
- [ ] ledger explains every lifecycle transition

**Exit Criteria:**
- no lifecycle mutation requires direct SQL or hidden state

### Wave 4: integrate run-scoped runtime residual

**Purpose:**
- personalize order without destabilizing baseline facts or runtime dependencies

**Steps:**
- [ ] resolve compatible active payload once per run
- [ ] persist exact resolved payload in checkpoint/run artifact
- [ ] assign baseline ranks across all scored eligible rows
- [ ] compute personalized projections through standard-library math
- [ ] order and truncate by raw personalized score
- [ ] persist row and stage diagnostics
- [ ] keep resume bound to original resolved payload
- [ ] prove CV analysis consumes baseline label only

**Verification:**
- [ ] active vector can reverse order while labels/CV gate remain unchanged
- [ ] unavailable storage yields visible zero fallback, not run failure
- [ ] runtime works without optional solver extras
- [ ] raw score, not clipped display score, owns order

**Exit Criteria:**
- production ranking is personalized, reproducible, solver-free, and label-stable

### Wave 5: documentation, deletion, and master closeout

**Purpose:**
- align source truth, generated discovery, and active code with completed phases

**Steps:**
- [ ] update feature and stage source contracts first
- [ ] update architecture, configuration, and pipeline docs
- [ ] regenerate architecture and planning metadata
- [ ] delete obsolete BM25/BM25F and learned-baseline-weight surfaces
- [ ] delete no-op ranking persistence hook after impact confirmation
- [ ] search for shadow active-policy or mutable rating state
- [ ] run focused, regression, import-isolation, lifecycle, and repo validators
- [ ] record closeout evidence in implementation plan

**Verification:**
- [ ] source search leaves one owner for every fact
- [ ] generated outputs match human-owned sources
- [ ] all seven master child specs/plans are terminal after implementation

**Exit Criteria:**
- master replacement closes without deferred lifecycle/runtime/docs/deletion work

## Design Decisions

### Decision: one solver-free runtime module

- context: Phase 6 optimizer may import optional solver stack; ranking must work
  without it
- choice: put payload validation, compatibility, lifecycle records, and residual
  math in `src/fitcv/preference_policy.py`
- alternatives considered:
  - import optimizer module from ranking
  - duplicate vector validation in store and ranking
- impact:
  - runtime remains solver-independent
  - one validator prevents boundary drift

### Decision: runtime compatibility excludes training tools

- context: solver/compiler/evaluation provenance matters before promotion but
  active vector needs fewer runtime contracts
- choice: candidate staleness uses full provenance; active resolution uses exact
  baseline, ranking, embedding, dimension, alpha, and norm contracts
- alternatives considered:
  - bind runtime to full decision-learning fingerprint
  - ignore contract versions after activation
- impact:
  - unsafe score contexts fall back
  - harmless solver upgrades do not disable valid active vector

### Decision: promotion uses non-regression plus strict gain

- context: one weighted promotion score would add hidden objective
- choice: candidate is non-worse on every required metric and strictly better on
  at least one decision metric against baseline and compatible parent
- alternatives considered:
  - one weighted evaluation score
  - manual activation without evaluation gate
- impact:
  - no new metric weights exist
  - gate is symmetric across comparator types

### Decision: zero residual is implicit baseline state

- context: fake zero-vector snapshots create churn and second baseline form
- choice: zero residual is typed resolver/lifecycle target, never learned snapshot
- alternatives considered:
  - create active zero snapshots
- impact:
  - fixed baseline remains canonical
  - rollback-to-baseline stays uniform

### Decision: raw personalized score owns order

- context: clipping can erase learned margins and create ties
- choice: rank by raw score; clip only display projection
- alternatives considered:
  - rank by clipped score
- impact:
  - runtime matches Phase 6 objective
  - clipping stays observable

### Decision: baseline rank and personalized rank remain distinct

- context: overwriting baseline rank destroys replay/evaluation evidence
- choice: preserve `baseline_rank`, add `personalized_rank`, keep legacy rank
  aliases baseline-derived
- alternatives considered:
  - reuse `baseline_rank`
  - redefine `final_rank`
- impact:
  - old semantics remain inspectable
  - personalized top N can be explained against baseline

### Decision: SQLite owns current active truth

- context: file flags or memory registries conflict with persistent lifecycle
- choice: derive active state from snapshot status, protected by partial unique
  index and transactions
- alternatives considered:
  - active-policy config field
  - separate current-policy table
- impact:
  - one active SSOT exists
  - concurrency uses native database behavior

### Decision: run freezes resolved payload

- context: activation during run/resume must not change semantics midway
- choice: resolve once, validate once, store exact payload, reuse through resume
- alternatives considered:
  - resolve for every ranking call
  - resolve again on resume
- impact:
  - one run has one policy identity
  - old runs remain reproducible

### Decision: no generic decision-domain framework yet

- context: only job-ranking preference learning exists
- choice: keep domain ID in contracts but implement job semantics directly;
  extract framework only after second domain proves same shape
- alternatives considered:
  - prebuild plugin and adapter interfaces
- impact:
  - minimum code and fewer speculative seams
  - symmetry comes from common functions, not premature framework

## Invariants

1. Star ratings remain append-only ordinal application-interest evidence.
2. Application history remains separate and is never inferred from ratings.
3. Fixed baseline weights are never solver variables or lifecycle payload data.
4. `baseline_fit` remains Phase 3 score under exact ranking contract.
5. `strong | stretch | skip` derives only from baseline score and thresholds.
6. Learned residual changes order only.
7. Raw personalized score owns ordering and pair evaluation.
8. Display clipping never changes ordering.
9. Baseline rank and personalized rank are distinct persisted facts.
10. One normalized runtime contract produces one fingerprint.
11. One immutable snapshot payload produces one payload fingerprint.
12. Snapshot preference vector is never edited in place.
13. Training-run evidence is immutable.
14. Lifecycle history is append-only.
15. At most one active snapshot exists per domain/runtime contract.
16. Candidate creation requires current store-verified evidence.
17. Candidate equivalent to zero or parent creates no snapshot.
18. Candidate activation requires exact current parent and bound fingerprints.
19. Changed evidence or training provenance makes candidate stale.
20. Active runtime compatibility ignores later solver-only provenance change.
21. Rollback restores exact prior payload or zero-residual baseline state.
22. Failed transaction leaves statuses and ledger unchanged.
23. Runtime imports no CVXPY or NumPy solely for residual math.
24. Missing/incompatible/invalid/unavailable policy visibly falls back to zero.
25. One run resolves one policy and resume reuses it.
26. Old run stores exact baseline, embedding, vector, residual, raw/display score,
    clipping flag, label, and policy identity.
27. Generated docs derive from human-owned feature/stage sources.
28. No active BM25/BM25F shortlist or learned-baseline-weight owner remains.
29. No parallel active-policy registry exists.
30. Shared infrastructure never shares evidence, vectors, semantic parameters,
    or activation authority across domains.

## Acceptance Criteria

- Phase 6 plan is terminal `completed`, commit `94793269` is current branch
  ancestor, and no unfinished Phase 6 behavior is hidden in Phase 7
- one solver-free module owns runtime payload validation and residual math
- activation policy has one config owner and no CLI/settings override
- native SQLite enforces lifecycle enum, parent kind, immutable payload, foreign
  keys, and one active compatible snapshot
- every terminal candidate attempt has one immutable training row
- no-op or promotion failure creates no snapshot
- stale candidate cannot activate
- two concurrent activations produce one active winner and explicit conflict
- rejection and staleness are terminal candidate states
- rollback restores exact prior vector or zero-residual baseline
- resolver returns one typed active/fallback result for every admissible case
- personalized order can change top N while baseline rank/label remain exact
- CV generation gates remain compatible when only order changes
- old run replay never consults current active policy
- runtime passes without optional solver dependency installed
- diagnostics expose factor, eligibility, retrieval, rating, edge, solver,
  stability, clipping, staleness, and active-payload evidence
- current docs describe Phase 7 runtime truth
- deletion search distinguishes shortlist BM25/BM25F from unrelated CV-analysis
  lexical evidence
- no generic second-domain framework is added
- generated metadata and repo validators pass

## Non-Goals

- automatic activation
- online or incremental optimization
- learning baseline factor weights
- changing rating scale, compiler semantics, or evidence budget
- application-history inference or migration
- BM25/BM25F or hybrid shortlist retrieval
- changes to location/language eligibility semantics
- personalized score bands or personalized CV gate
- admin web UI for policy lifecycle
- remote database or distributed lock support
- generic policy plugin system
- policy snapshot deletion or history compaction
- automatic rollback from production metrics
- changing solver, alpha, margin, regularization, or norm bound

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| residual dominates baseline | fixed alpha, norm bound, validation, clipping/rank-change diagnostics |
| stale candidate activates | compare parent, config, runtime, cohort, and edges inside transaction |
| two active policies | `BEGIN IMMEDIATE`, partial unique index, explicit conflict |
| solver upgrade disables valid active vector | runtime contract excludes solver provenance |
| corrupt payload breaks run | validate once and visibly fall back to zero |
| fallback masks storage outage | persist resolution status/diagnostic in run and rows |
| resume picks newer policy | freeze resolved payload in checkpoint |
| display clipping changes rank | raw score is sole order key |
| learned order changes CV gate | downstream reads baseline label only; reversal tests |
| duplicated evidence drifts | frozen JSON/fingerprints match referenced training row |
| unrelated lexical code deleted | cleanup limited to shortlist BM25/BM25F |
| generic abstraction adds drift | wait for second concrete domain |
| transaction leaves partial history | shared transaction and rollback tests |

## Validation Plan

- proof target: Phase 6 is complete and Phase 7 is only remaining master phase
  - method: inspect master phase graph, Phase 6 terminal plan, Git commit, and
    child-spec inventory
  - evidence: seven phases total; specs exist for 1–6; Phase 6 plan completed at
    `94793269`; only Phase 7 spec was missing
- proof target: runtime module is solver-independent
  - method: import/scoring tests without optional solver extra; source search
  - evidence: policy resolution and ranking succeed without CVXPY, CLARABEL, or
    NumPy import
- proof target: runtime equations are deterministic and symmetric
  - method: exact fixtures, row/vector permutation, vector sign/swap, and
    repeated canonical JSON comparison
  - evidence: equal normalized inputs yield equal residuals/fingerprints; row
    permutation preserves score and total order
- proof target: payloads are immutable and complete
  - method: schema tests, forbidden updates, malformed JSON, fingerprint mismatch,
    and referenced-training mismatch tests
  - evidence: SQLite rejects mutation/corruption; accepted payload contains full
    Layer 11 provenance
- proof target: candidate promotion is uniform
  - method: table-driven comparisons against baseline and parent for equal,
    better, worse, missing, tolerance-boundary, and reversed-stability cases
  - evidence: one comparator returns deterministic gate reasons
- proof target: no-op suppression prevents churn
  - method: zero, parent-equal, within/outside tolerance, permutation, and
    dimension-error fixtures
  - evidence: equivalent result persists training row only; distinct passing
    vector creates one candidate
- proof target: evidence changes stale candidate
  - method: append/clear rating, add compatible episode, and change compiler,
    optimizer, solver, evaluation, activation, baseline, ranking, or embedding
    contracts between candidate and activation
  - evidence: each bound change blocks activation and appends exact stale reason
- proof target: active compatibility is narrower than candidate staleness
  - method: change solver/evaluation provenance after activation while preserving
    runtime contract; then change each runtime field
  - evidence: solver-only change retains vector; runtime change yields fallback
- proof target: activation is compare-and-swap safe
  - method: two SQLite connections activate sibling candidates with same parent
  - evidence: one succeeds; loser is stale/conflict; one active row remains
- proof target: rollback is exact and auditable
  - method: activate A, activate B, rollback A, rollback zero, inspect all rows
  - evidence: original A payload fingerprint returns; zero leaves no active row;
    ledger records retire/activate/rollback sequence
- proof target: failed transaction is atomic
  - method: inject event-insert and status-update failures
  - evidence: no partial lifecycle state or orphan event remains
- proof target: run policy is frozen
  - method: start run with A, activate B before ranking/resume, complete run
  - evidence: original run/resume use A; new run uses B
- proof target: downstream labels remain baseline-derived
  - method: reverse order and top-N membership with personalized residual
  - evidence: baseline label, fit aliases, CV gate, and strong/stretch/skip counts
    remain unchanged
- proof target: raw score owns order
  - method: fixtures where multiple raw scores clip to same display value
  - evidence: raw order stays distinct and clipping flags persist
- proof target: fallback is visible and safe
  - method: absent, incompatible, malformed, over-norm, duplicate-active, locked,
    unreadable, and corrupt-DB fixtures
  - evidence: run continues on baseline with exact fallback status; mutation
    commands fail rather than pretend success
- proof target: diagnostics compose existing SSOTs
  - method: inspect CLI golden fixtures with/without run ID and missing audit labels
  - evidence: required categories appear; unavailable evidence is explicit
- proof target: obsolete truth is removed
  - method: scoped searches for BM25/BM25F shortlist, learned baseline weight,
    alternate active policy, mutable current rating, Phase 6 no-runtime wording,
    and dead ranking persistence hook
  - evidence: only history or unrelated CV-analysis lexical evidence remains
- proof target: docs and generated surfaces stay source-derived
  - method: architecture/planning generation, lifecycle/repo validation, diff check
  - evidence: generated outputs current; no generated file hand-edited

Recommended implementation verification:

```text
python -m pytest tests/test_config.py tests/test_preference_policy.py tests/test_inverse_optimization.py -q
python -m pytest tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_sqlite_store.py -q -k "preference_policy or inverse_training or activation"
python -m pytest tests/test_ranking.py tests/test_ranking_contract.py tests/test_ai_score.py -q
python -m pytest tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py -q
python -m pytest tests/test_decision_feedback.py tests/test_fitcv_cp/test_app.py -q
python -m ruff check src/fitcv/preference_policy.py src/fitcv/inverse_optimization.py src/fitcv/ranking.py src/fitcv/pipeline.py src/fitcv/pipeline_stage_runner.py src/fitcv/pipeline_stage_artifacts.py src/fitcv/agentic_cv_analysis.py src/fitcv_cp/store.py src/fitcv_cp/sqlite_store.py scripts/run_inverse_optimization.py tests/test_preference_policy.py
uvx mypy src/fitcv/preference_policy.py src/fitcv/inverse_optimization.py src/fitcv/ranking.py src/fitcv_cp/store.py src/fitcv_cp/sqlite_store.py --show-error-codes --follow-imports=skip
python tools/docs/generate_architecture_metadata.py
python scripts/generate_planning_lineage.py
python tools/docs/generate_architecture_metadata.py --check
python scripts/validate_planning_lifecycle.py
python scripts/hooks/run_validator.py --fast
python scripts/validate_repo_contracts.py --fast
git diff --check
```

Scope and deletion proof:

```text
rg -n "cvxpy|clarabel|numpy" src/fitcv/preference_policy.py src/fitcv/ranking.py src/fitcv/pipeline.py src/fitcv/pipeline_stage_runner.py
rg -n -i "bm25f?|shortlist_lexical|hybrid.?retrieval|learn(ed|ing).*(baseline|weight)|preference_weights" config src tests docs --glob "!docs/superpowers/archive/**" --glob "!docs/superpowers/specs/**" --glob "!docs/superpowers/plans/**"
rg -n "active_policy|current_policy|policy_snapshot" config src tests docs --glob "!docs/superpowers/**"
rg -n "baseline_fit_label|personalized_rank_score|personalized_display_score" src/fitcv/agentic_cv_analysis.py src/fitcv/pipeline.py src/fitcv/ranking.py
```

Expected: solver imports absent from runtime path; no active shortlist
BM25/BM25F or learned-baseline-weight owner; one SQLite snapshot registry; CV
gate reads baseline label only.

## Completion Criteria

Phase 7 implementation is complete when:

1. all Key Deliverables and Acceptance Criteria pass
2. one solver-free module owns runtime policy validation and score projection
3. one activation policy block owns mutable lifecycle numeric policy
4. immutable training runs, snapshots, and activation events use one SQLite owner
5. candidate creation verifies current evidence, passes uniform gate, and
   suppresses zero/parent-equivalent churn
6. reject, activate, and rollback are manual typed commands
7. activation and rollback are transactional compare-and-swap operations
8. one-active constraint and concurrent-operation tests pass
9. run resolves one compatible payload once and stores exact payload for resume
10. runtime residual uses standard-library math and no solver dependency
11. raw personalized score owns order; display score clips only for UI
12. baseline score, rank, label, and downstream CV gate remain authoritative
13. old runs retain exact policy and score evidence after lifecycle changes
14. every fallback is visible and preserves baseline behavior
15. observability covers all master-required evidence categories
16. human-owned docs describe runtime truth; generated outputs synchronize
17. obsolete BM25/BM25F shortlist, learned-baseline-weight, shadow state, dead
    adapters, and temporary migration paths are deleted or proven absent
18. no speculative multi-domain framework exists
19. implementation plan is completed with fresh verification evidence
20. every child item is `completed` or `dropped`
21. master inverse-optimization replacement satisfies final closeout criteria

Canonical source-of-truth:

<LINK>
- `docs/superpowers/specs/2026-07-14-22-25-fitcv-inverse-optimization-master-ssot-symmetry-spec.md`
- `docs/superpowers/specs/2026-07-16-09-31-fitcv-inverse-optimization-phase-6-latent-residual-solver-evaluation-spec.md`
- `docs/superpowers/plans/2026-07-16-09-55-fitcv-inverse-optimization-phase-6-latent-residual-solver-evaluation-plan.md`
- `config/policy/decision_learning.yaml`
- `config/policy/ranking.yaml`
- `src/fitcv/decision_feedback.py`
- `src/fitcv/inverse_optimization.py`
- `src/fitcv/ranking_contract.py`
- `src/fitcv/ranking.py`
- `src/fitcv_cp/sqlite_store.py`
- `docs/stages/ranking.source.yaml`
- `docs/stages/cv_analysis.source.yaml`
- `docs/features/cv_system/feature.source.yaml`
- `docs/operating_system/governance/repo-governance.md`
- `docs/operating_system/lifecycle/doc-system-lifecycle.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
