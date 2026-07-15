---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: fitcv-inverse-optimization-master-ssot-symmetry
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-stage-authority-contract
targets:
  - config/policy/eligibility.yaml
  - config/policy/ranking.yaml
  - config/policy/decision_learning.yaml
  - config/shortlist_lexical.yaml
  - pyproject.toml
  - uv.lock
  - src/fitcv/config.py
  - src/fitcv/ingest.py
  - src/fitcv/normalize.py
  - src/fitcv/enrich.py
  - src/fitcv/fit_factors.py
  - src/fitcv/rule_filter.py
  - src/fitcv/vector_search.py
  - src/fitcv/embeddings.py
  - src/fitcv/ranking_contract.py
  - src/fitcv/ranking.py
  - src/fitcv/ai_score.py
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_runner.py
  - src/fitcv/decision_feedback.py
  - src/fitcv/inverse_optimization.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/store.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/templates/run_detail_tab_enriched.html
  - scripts/run_inverse_optimization.py
  - docs/architecture.md
  - docs/configuration.md
  - docs/pipeline.md
  - docs/stages/normalize.source.yaml
  - docs/stages/enrich.source.yaml
  - docs/stages/rule_filter.source.yaml
  - docs/stages/shortlist.source.yaml
  - docs/stages/ranking.source.yaml
  - docs/stages/cv_analysis.source.yaml
  - docs/features/cv_system/feature.source.yaml
  - docs/superpowers/specs/2026-05-28-14-09-shortlist-hybrid-retrieval-spec.md
  - docs/superpowers/specs/2026-05-28-16-14-shortlist-bm25-upgrade-spec.md
  - docs/superpowers/plans/2026-05-28-14-14-shortlist-hybrid-retrieval-plan.md
  - docs/superpowers/plans/2026-05-28-16-18-shortlist-bm25-upgrade-plan.md
  - tests/test_normalize.py
  - tests/test_ingest.py
  - tests/test_enrich.py
  - tests/test_rule_filter.py
  - tests/test_vector_search.py
  - tests/test_decision_feedback.py
  - tests/test_inverse_optimization.py
  - tests/test_ranking.py
  - tests/test_ai_score.py
  - tests/test_pipeline.py
  - tests/test_pipeline_stage_resume_parity.py
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
  - normalize
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
---

# Detailed Spec: FitCV inverse optimization master SSOT and symmetry

## Goal

Define one canonical, symmetric FitCV ranking system that:

- adds actual-location and language-requirement facts as versioned eligibility and ranking inputs
- removes unused BM25/BM25F scaffolding and keeps shortlist retrieval vector-only until measured recall evidence justifies another channel
- replaces the flat six-factor final score with a fixed robust baseline plus one small learned embedding-space preference adjustment
- learns from low-friction 1–5-star ratings while preserving every rating as ordinal source truth

The system must behave uniformly across every admissible case, including no ratings, one rating, repeated or cleared ratings, equal ratings, ambiguous or clear rating gaps, incompatible contracts, weak or collinear latent evidence, contradictory evidence, solver failure, stale candidates, concurrent activation, and rollback.

The canonical flow is:

`NormalizedJob -> EnrichedFitFacts -> EligibilityEvaluation -> VectorShortlist -> BaselineRankingArtifact -> DecisionEpisode -> RatingEvent -> EffectiveRating -> PreferenceEdge -> InverseProblem -> CandidatePreferencePayload -> Evaluation -> Activation`

Each arrow is a boundary adapter. No downstream layer recomputes or redefines upstream truth.

This master specification defines ownership, contracts, ordered phases, required child specifications, invariants, acceptance criteria, and validation evidence. It does not authorize implementation or a big-bang rewrite.

## Triage

- layer: `change`
- feature type: `REPLACE`
- summary: replace unused lexical scaffolding and flat ranking-weight learning with versioned eligibility facts, vector-only retrieval, a fixed baseline, and one bounded latent preference residual
- affected stages: `normalize`, `enrich`, `rule_filter`, `shortlist`, `ranking`, `cv_analysis`
- affected features: `cv_system`, `admin_control_plane_core`, `inspection_debugging`, `settings_system`
- spec needed: yes
- plan needed: no until this master spec and required child specs are approved

## Key Deliverables

### Deliverable 1: one SSOT ownership model

| Fact | Canonical owner |
| --- | --- |
| raw job location text and source language evidence | normalized and enriched job contracts |
| canonical actual-location and language-requirement facts | `src/fitcv/enrich.py` output contract |
| factor evaluator result shape and factor-specific normalization | `src/fitcv/fit_factors.py` |
| hard-constraint policy modes and mappings | `config/policy/eligibility.yaml` |
| structured factor names and score-composition semantics | `src/fitcv/ranking_contract.py` plus ranking feature functions |
| baseline numeric ranking policy | `config/policy/ranking.yaml` |
| decision-learning policy | `config/policy/decision_learning.yaml` |
| vector retrieval behavior | `src/fitcv/vector_search.py` plus existing embedding contract |
| run-time baseline score, normalized job embedding, and ranking evidence | immutable ranking stage artifact |
| frozen training alternatives | immutable decision-episode snapshot derived from ranking artifact |
| user judgment | append-only rating event ledger |
| current rating state | deterministic reduction of rating events |
| preference comparisons | deterministic compiler output |
| learned policy | immutable candidate or active policy payload with lifecycle state |
| run-time policy selection | active-payload resolver plus run-scoped policy fingerprint |
| activation and rollback history | append-only activation event ledger |

SSOT means one authority per fact, not one physical file for unrelated truths.

### Deliverable 2: one symmetric decision algebra

Every supported rating case normalizes through the same primitive:

`preferred alternative -> non-preferred alternative`

The compiler contains no UI-specific solver branches. It accepts effective ordinal ratings and produces deterministic weighted preference edges.

Rating semantics are versioned and explicit:

```text
1 = definitely not interested
2 = low application interest
3 = might consider applying
4 = strong application interest
5 = would prioritize applying
```

Stars express personal application interest after eligibility. They do not restate qualification, predict application completion, or directly define cardinal utility.

### Deliverable 3: one native-first rating and persistence path

Use native or already-owned components first:

- HTML forms, buttons, labels, and CSS
- existing FastAPI form handling
- `enum.IntEnum` and frozen `dataclasses.dataclass`
- `sqlite3` transactions, constraints, foreign keys, and indexes
- `json`, `hashlib`, `uuid`, `datetime`, and `argparse`
- existing config loader, run-store boundary, ranking artifacts, and job fingerprints

Do not recreate browser form behavior, database constraints, JSON encoding, hashing, UUID generation, timestamps, or argument parsing in custom frameworks.

### Deliverable 4: one fixed baseline and one bounded optimization dependency

Use CVXPY only in offline training/evaluation code. Runtime ranking, rating UI, event storage, effective-state reduction, and activation remain usable without importing CVXPY, NumPy, or solver packages.

First runtime score contract:

```text
baseline_fit =
  holistic_ai_weight * holistic_ai_fit
  + structured_weight * structured_fit

personalized_rank_score =
  baseline_fit + learned_alpha * dot(preference_vector, normalized_job_embedding)

personalized_display_score = clamp(personalized_rank_score, 0, 1)
```

Ordering and pairwise evaluation use raw `personalized_rank_score`. Clipping is display-only and cannot create ranking ties. `strong`, `stretch`, and `skip` remain derived from `baseline_fit` in first implementation. Learned residual changes ordering only; it does not change downstream CV eligibility until a separately approved absolute ordinal-calibration contract exists.

First solver contract:

- CVXPY modeling layer
- one explicit conic-capable convex solver selected by policy and validated in CI
- strictly convex L2 distance from the zero preference vector
- nonnegative per-edge slack
- one unit-norm bound on the learned preference vector
- deterministic solver options
- typed statuses and independent residual validation

No custom optimizer is allowed while a maintained predefined solver correctly implements the convex program.

### Deliverable 5: one immutable policy payload with lifecycle state

Training produces candidate payload only. Payload fields never change. Evaluation, activation, rejection, staleness, retirement, and rollback remain controlled lifecycle transitions. Old runs keep exact policy payload and fingerprint used originally.

### Deliverable 6: one explicit child-spec dependency graph

Required child detailed specs:

1. location/language fact, evaluator, normalization, and eligibility-policy contract
2. vector-only shortlist contract and BM25/BM25F deletion
3. fixed baseline ranking-v2 contract, downstream label ownership, and globally versioned score normalization
4. decision episode, rating ledger, and native star-rating surface
5. effective-rating reducer and deterministic preference compiler
6. CVXPY latent-residual solver and episode-grouped evaluation
7. preference policy-payload registry, activation, rollback, runtime use, observability, docs, and closeout deletion

Numbering identifies scope, not mandatory total ordering. BM25 cleanup and rating capture may proceed independently when their prerequisites are satisfied. No implementation plan may combine scopes before required child specs exist and inherit this master spec.

## Current-State Diagnosis

### Existing reusable owners

- `src/fitcv/ranking.py`: six features and weighted final score
- `src/fitcv/ranking_contract.py`: weight and threshold validation
- `src/fitcv/normalize.py`: raw field normalization and deduplication
- `src/fitcv/enrich.py`: structured extraction, canonicalization, reuse, and enriched-row persistence contract
- `src/fitcv/rule_filter.py`: deterministic eligibility boundary before shortlist
- `src/fitcv/vector_search.py`: actual cosine-based vector retrieval and reusable job/candidate embeddings
- `src/fitcv/embeddings.py`: job-summary embedding input contract
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

The current shortlist lexical surface is also misleading: `config/shortlist_lexical.yaml`, BM25/BM25F formula labels, protected-term payloads, and debug hashes exist, but runtime shortlist ordering is cosine-only. The final implementation deletes that unused policy and observability surface instead of preserving a false retrieval channel.

### Existing gaps

The project preserves ranking evidence but has no active application history or rating ledger. Historical preference cannot be reconstructed from past browsing. Learning starts from future explicit ratings only.

The enriched fit context has `location_type` but not one canonical actual-location structure, and it has no canonical per-job language-requirement structure with expected levels. These facts must exist before they can act as either ranking factors or confirmed-failure hard constraints.

Current ranking mixes `vector_similarity` into the final weighted score and retains the AI-produced fit label as downstream gate truth. Ranking-v2 moves vector similarity back to retrieval-only use, maps raw `ai_score` to `holistic_ai_fit` at the ranking boundary, and derives downstream `strong|stretch|skip` from the fixed baseline score.

## Canonical Architecture

### Layer 1: canonical fit facts and factor evaluation

Pipeline `normalize` owns raw scalar cleanup and stable source preservation. `enrich` owns extracted actual-location and language-requirement facts. Candidate-dependent acceptance remains outside pipeline normalization.

Canonical job facts:

```text
actual_location:
  raw_text
  city
  region
  country
  remote_scope
  extraction_status

language_requirements[]:
  language
  expected_level
  requirement_type: required | preferred | unspecified
  extraction_status
```

Every structured evaluator returns one shape:

```text
status: pass | fail | unknown | not_applicable
score: optional finite float in [0, 1]
confidence: finite float in [0, 1]
reason_code
evidence
evaluator_version
normalizer_version
```

Evaluator truth and policy decision are separate. `config/policy/eligibility.yaml` maps evaluator status to:

```text
mode: disabled | ranking_only | gate_required
eligibility_decision: retain | reject
ranking_value: finite float in [0, 1]
ranking_enabled: true | false
```

Rules:

- `gate_required` rejects confirmed `fail` only; `unknown` passes with diagnostic
- a factor used as a hard gate has zero ranking weight in that policy version
- unknown and not-applicable mappings are factor-specific, never one universal `0.5`
- active ranking-factor weights are normalized once when validated policy context loads:

```text
active_ranking_factors = factors whose mode is ranking_only
effective_weight[f] = configured_weight[f] / sum(configured_weight[g] for g in active_ranking_factors)
```

- disabled and hard-gated factors receive zero effective weight
- policy-level effective weights and their fingerprint remain fixed for every job in run; no per-job weight renormalization occurs
- candidate-specific rejection happens in `rule_filter`; every downstream score-normalization input and shortlist receives retained candidates only

### Layer 2: policy contracts

Canonical files:

- `config/policy/eligibility.yaml`: language/location modes, status projections, factor-specific missing semantics, and policy version
- `config/policy/ranking.yaml`: fixed baseline channel weights, configured structured-factor weights, factor/normalizer versions, and baseline fit-label thresholds
- `config/policy/decision_learning.yaml`: rating scale, clear-gap compiler policy, learned alpha, vector norm bound, optimizer, solver, evaluation, and activation policy

Code owns executable semantics, admissible names, types, ranges, validation, and policy-level effective-weight derivation. Config owns mutable numeric policy only. Ranking contract fingerprint includes eligibility policy version and effective weights.

Canonical structured ranking factors:

1. `must_have_match`
2. `title_relevance`
3. `seniority_fit`
4. `declared_preference_fit`
5. `location_fit`
6. `language_fit`

Raw `ai_score` remains the AI-stage output and maps once to `holistic_ai_fit` at the ranking boundary. `vector_similarity` and `vector_rank` remain retrieval evidence, not baseline ranking factors.

### Layer 3: vector shortlist and baseline ranking artifact

Shortlist retrieval is cosine/vector-only in first implementation:

```text
eligible jobs -> vector_similarity -> vector_rank -> Top N scoring shortlist
```

The row contract preserves `job_url`, `vector_similarity`, `vector_rank`, and `shortlist_origin`. BM25/BM25F config, formula labels, protected-term payloads, hashes, and hybrid-retrieval claims are deleted.

Ranking-v2 computes:

```text
structured_fit = sum(fixed_structured_weight[k] * structured_factor[k])

baseline_fit =
  holistic_ai_weight * holistic_ai_fit
  + structured_weight * structured_fit

baseline_fit_label = thresholds(baseline_fit)
```

Combined baseline is not accepted by construction. Phase 3 must compare:

```text
A = current holistic AI baseline
B = structured baseline only
C = proposed holistic AI + structured baseline
```

`C` becomes production baseline only when it improves approved qualification benchmark and stays within approved `strong|stretch|skip` migration limits. Otherwise current holistic AI baseline remains authoritative and structured factors remain diagnostic until later evidence supports promotion.

The immutable ranking artifact stores:

```text
baseline_fit
baseline_fit_label
structured factors and contributions
eligibility evaluations and policy decisions
normalized_job_embedding
embedding_model
embedding_dimension
embedding_contract_fingerprint
embedding_vector_hash
ranking_contract_fingerprint
normalizer_version
baseline_policy_fingerprint
```

The learned preference residual later changes ordering only. `baseline_fit_label` remains authoritative for downstream `strong|stretch|skip` in first implementation.

Vector-retrieval recall is measured through bounded deterministic audit/exploration sample below production cutoff. Audit rows use explicit `shortlist_origin: audit`, appear in same review/rating surface, and remain excluded from production ranking unless normal shortlist rule selects them. Jobs never exposed to review cannot be counted as observed retrieval misses.

### Layer 4: decision episode

Episode fields:

```text
episode_id
domain_id
run_id
preference_context_fingerprint
qualification_context_fingerprint
ranking_contract_fingerprint
embedding_contract_fingerprint
baseline_policy_fingerprint
rating_scale_version
candidate_set_fingerprint
source_stage_artifact_fingerprint
created_at
```

Alternative fields:

```text
episode_id
alternative_id
displayed_rank
baseline_fit
baseline_fit_label
normalized_embedding_json
embedding_vector_fingerprint
source_job_url
created_at
```

Rules:

- alternative identity is stable `raw_job_fingerprint`
- URL is descriptive metadata only
- baseline score and normalized embedding are copied from immutable ranking artifact, never recomputed
- copied values are provenance-bound archival evidence, not competing truth
- `preference_context_fingerprint` identifies stable user preference scope; it must not hash entire mutable CV/profile document
- `qualification_context_fingerprint` preserves baseline qualification context for replay without automatically dividing preference cohorts
- one episode contains one compatible ranking, embedding, baseline, preference, qualification, and rating-scale context
- `episode_id` is stable fingerprint of one canonical payload:

```text
domain_id
run_id
preference_context_fingerprint
qualification_context_fingerprint
ranking_contract_fingerprint
baseline_policy_fingerprint
embedding_contract_fingerprint
rating_scale_version
candidate_set_fingerprint
source_stage_artifact_fingerprint
```

- same canonical payload owns episode ID, database identity, lookup, materialization idempotency, and fingerprint tests
- first rating POST may materialize episode atomically when absent
- GET routes do not create or mutate episode state

### Layer 5: append-only rating event

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
- rating scale version resolves exact personal-application-interest labels defined by decision-learning policy
- event ordering uses `(created_at, event_id)`
- no mutable `current_rating` column exists as competing truth

### Layer 6: effective rating reducer

Effective rating is derived from the latest event for each `(episode_id, alternative_id)`.

Use SQLite ordering/window semantics or one shared Python reducer over ordered rows. Do not maintain a UI cache, JSON shadow state, or second current-state table.

Reducer outputs `unrated | 1 | 2 | 3 | 4 | 5`. `clear_rating` reduces to `unrated`.

### Layer 7: preference compiler

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
episode_bounded_weight
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

`source_event_ids` contains exactly two event IDs that produced current effective ratings for edge endpoints. Complete reduction history remains in append-only ledger and is bounded by training event watermark.

Capped episode budgeting preserves absolute gap evidence while limiting large episodes:

```text
episode_scale = min(
  1,
  max_episode_evidence_budget / sum(gap_evidence_weight for episode edges)
)

episode_bounded_weight = gap_evidence_weight * episode_scale
```

`max_episode_evidence_budget` is positive versioned policy. Larger configured rating gap must retain greater edge weight than smaller gap under same policy, including one-edge episodes.

An empty edge set is valid and produces `insufficient_evidence`, not an error.

### Layer 8: inverse problem

For each directed edge `i > j`, freeze baseline scores `B_i`, `B_j` and normalized embeddings `z_i`, `z_j` from episode evidence. First implementation learns only one bounded latent preference residual `p`; fixed structured and holistic baseline weights remain unchanged.

Training uses full refit, not incremental deltas:

1. select one compatible cohort
2. load all rating events through chosen `event_watermark`
3. reduce complete event history to effective ratings
4. rebuild complete current edge set
5. fit `p` from zero using that full evidence snapshot

Active parent vector is comparison, concurrency, and rollback reference only. It is not optimization prior in first implementation.

```text
p0 = zero vector

minimize
  preference_regularization * sum_squares(p - p0)
  + sum(edge_weight[e] * slack[e])

subject to
  (B_i - B_j) + learned_alpha * p @ (z_i - z_j)
    >= preference_margin - slack[e]
  norm(p, 2) <= 1
  slack >= 0
```

Rationale:

- fixed baseline preserves current explicit scoring semantics and score-band meaning
- zero-centered L2 regularization chooses the smallest latent correction supported by evidence
- fixed small `learned_alpha` caps learned influence and remains one versioned policy value
- nonnegative slack keeps contradictory evidence feasible
- unit-ball constraint prevents an unsupported latent vector from dominating baseline ranking
- one explicit solver and option set makes offline execution reproducible enough for policy lifecycle

No `tanh`, logit transform, learned factor weights, simplex, or per-feature learned bounds are allowed in first implementation. Boundary code adapts plain Python values to solver-native arrays once. No application-specific matrix class is allowed.

### Layer 9: solver result

```text
status:
  optimal
  insufficient_evidence
  invalid_input
  infeasible_policy
  solver_error
candidate_preference_vector
objective_value
max_preference_violation
preference_vector_norm
vector_norm_residual
embedding_model
embedding_dimension
embedding_contract_fingerprint
learned_alpha
solver_name
solver_version
solver_options_fingerprint
problem_fingerprint
```

`optimal_inaccurate` is not silently accepted. First implementation rejects it as candidate input unless later versioned policy explicitly changes that rule. Independent post-solver checks recompute vector norm and every preference residual from plain values.

### Layer 10: evaluation

Edges from same episode are correlated. Evaluation splits by episode, never random edge.

Evaluation modes:

- leave-one-episode-out when evidence is small but sufficient
- grouped train/validation split when more episodes exist
- time-ordered grouped evaluation when preference-drift evaluation is enabled

Required comparisons:

- candidate residual vs zero-residual baseline and, when present, compatible active parent residual
- held-out pair agreement and preference violation rate
- held-out weighted slack or regret
- preference-vector norm and stability across episode resamples
- personalized-score clipping frequency
- episode, rating-gap, location, language, and baseline-label coverage
- vector-shortlist audit recall against bounded deterministic below-cutoff sample
- candidate ranking changes relative to baseline ordering

Counts are prerequisites only. Edge count does not prove stable latent direction or retrieval coverage.

### Layer 11: immutable policy payloads with lifecycle state

```text
policy_snapshot_id
domain_id
ranking_contract_fingerprint
baseline_policy_fingerprint
embedding_model
embedding_dimension
embedding_contract_fingerprint
learned_alpha
parent_policy_kind: zero_residual | learned
parent_policy_ref
status: candidate | active | rejected | stale | retired
preference_vector_json
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

- payload fields are immutable after creation; only lifecycle fields `status` and `activated_at` may change through transactional lifecycle operations
- preference vectors are never edited in place
- candidate references exact effective parent as either `zero_residual:<baseline_policy_fingerprint>` or `learned:<policy_snapshot_id>`
- candidate binds exact baseline, ranking, embedding, compiler, evidence, optimizer, and `learned_alpha` contracts
- equivalent candidate within configured tolerance creates no new snapshot
- candidate becomes stale before activation if rating inputs, training provenance, or any bound contract changes
- active runtime compatibility depends only on materialized vector plus baseline, ranking, embedding, dimension, alpha, and norm contracts; later solver-version changes do not invalidate already active compatible vector

### Layer 12: activation, rollback, and runtime integration

Activation uses one SQLite transaction:

1. load candidate
2. verify candidate status is `candidate`
3. verify candidate parent reference equals current effective parent reference
4. verify baseline, ranking, embedding, evidence, compiler, optimizer, and evaluation fingerprints remain current
5. retire previous active snapshot
6. activate candidate
7. append activation event
8. commit

Rollback uses same mechanism with a previous compatible snapshot as target. Concurrent activation uses compare-and-swap semantics. A stale candidate cannot replace newer active policy.

At run start:

1. load fixed baseline ranking policy from config
2. resolve one active learned payload compatible with baseline, ranking, embedding, dimension, alpha, and vector-norm contracts
3. validate preference vector dimension, finiteness, norm, and `learned_alpha`
4. compute latent residual with runtime-native or standard-library dot-product math
5. compute raw `personalized_rank_score` and clipped `personalized_display_score`
6. order jobs and evaluate pairs with raw score only
7. preserve `strong | stretch | skip` from persisted `baseline_fit`, not personalized score
8. record baseline score, residual, raw rank score, clipped display score, `score_was_clipped`, payload ID, and fingerprints in ranking artifact

Runtime ranking does not call optimizer and does not import CVXPY or NumPy solely for dot-product math.

Fallback behavior:

- no active snapshot -> zero residual over fixed baseline
- incompatible embedding, ranking, or baseline snapshot -> zero residual plus diagnostic
- invalid snapshot -> zero residual plus failure diagnostic
- persistence unavailable -> zero residual; no hidden memory-only active policy

## Admissibility Contract

An input is admissible when all conditions hold:

- domain ID and rating-scale version are supported by validated decision-learning policy
- each episode, when present, references one immutable ranking artifact, one stable preference context, and one qualification context
- every alternative has unique stable identity, finite `baseline_fit`, baseline label, and one frozen normalized embedding
- every embedding matches one model, dimension, normalization rule, and embedding-contract fingerprint
- location and language evaluator results follow canonical status, score, confidence, reason, evidence, and version contracts
- hard eligibility decisions are already projected before score normalization and shortlist ranking
- effective ratings are `unrated` or valid labels from episode scale
- every nonempty training cohort shares domain, preference context, ranking contract, baseline policy, embedding contract, rating scale, compiler version, and optimizer policy; qualification context remains frozen per episode for replay
- `learned_alpha`, preference margin, and positive regularization are finite and valid
- solver name and option set are supported by installed offline environment when a nonempty trainable problem reaches solver boundary

No evidence, one rating, equal ratings, below-gap ratings, contradictory preferences, collinear embedding differences, unknown optional facts, or zero useful latent direction are admissible states. They produce typed empty, diagnostic, or regularized results through normal flow.

Malformed ratings, unknown alternatives, nonfinite scores or embeddings, mixed contracts, embedding dimension mismatch, invalid `learned_alpha`, unsupported solvers, or corrupt fingerprints are invalid inputs. They fail at nearest owning boundary before optimization and never create candidate.

Uniform handling means every admissible input follows same fact evaluation, policy projection, reduction, compilation, optimization-result, evaluation, and lifecycle interfaces. Uniform does not mean every state produces edge, candidate, or learned score change.

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
| incompatible embedding contracts | separate episodes/cohorts | no cross-contract edges | separate training | no mixed snapshot |
| incompatible rating scale | separate version cohort or validation failure | no mixed edges | separate training | none |
| zero compiled edges | valid empty set | empty | insufficient evidence | none |
| collinear or weak latent evidence | valid diagnostics | edges retained | zero-centered regularized candidate | activation requires stability gate |
| hard location/language failure | fact retained with evidence | alternative absent from eligible episode | not trainable in that episode | none |
| unknown location/language fact | fact retained with diagnostic | follows configured policy mode | admissible | none by itself |
| invalid embedding dimension | boundary rejection | not applicable | invalid input | none |
| solver failure | evidence retained | edges retained | solver error | active policy unchanged |
| candidate equals zero or parent residual | evidence retained | edges retained | no-op | no snapshot churn |
| baseline, ranking, embedding, compiler, or evidence contract changes before activation | candidate retained | not applicable | candidate stale | activation blocked |
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
episode_id = stable fingerprint of canonical Layer 4 episode payload
NOT NULL domain_id
NOT NULL run_id
NOT NULL preference_context_fingerprint
NOT NULL qualification_context_fingerprint
NOT NULL ranking_contract_fingerprint
NOT NULL baseline_policy_fingerprint
NOT NULL embedding_contract_fingerprint
NOT NULL rating_scale_version
NOT NULL candidate_set_fingerprint
NOT NULL source_stage_artifact_fingerprint
```

### `decision_episode_alternatives`

```text
PRIMARY KEY episode_id, alternative_id
FOREIGN KEY episode_id -> decision_episodes
NOT NULL baseline_fit
NOT NULL baseline_fit_label
NOT NULL normalized_embedding_json
NOT NULL embedding_vector_fingerprint
NOT NULL embedding_dimension
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
ranking_contract_fingerprint
embedding_contract_fingerprint
embedding_dimension
learned_alpha
parent_policy_kind
parent_policy_ref
status
result_json
created_at
```

### `ranking_policy_snapshots`

```text
PRIMARY KEY policy_snapshot_id
NOT NULL domain_id
NOT NULL baseline_policy_fingerprint
NOT NULL ranking_contract_fingerprint
NOT NULL embedding_model
NOT NULL embedding_contract_fingerprint
NOT NULL embedding_dimension
NOT NULL learned_alpha
NOT NULL preference_vector_json
NOT NULL training_run_id
NOT NULL event_watermark
NOT NULL edge_set_fingerprint
NOT NULL compiler_version
NOT NULL optimizer_policy_fingerprint
NOT NULL solver_metadata_json
NOT NULL evaluation_json
CHECK parent_policy_kind in zero_residual, learned
NOT NULL parent_policy_ref
status constrained to lifecycle enum
NOT NULL created_at
activated_at nullable
one active snapshot per domain, ranking contract, embedding contract, and baseline policy fingerprint
```

This table is full persisted Layer 11 record, not key-only excerpt. Payload columns are immutable; lifecycle columns change only through owned transactional operations.

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

Each numbered scope requires its own approved child detailed specification before implementation. A child spec may refine local names and schemas, but it must inherit this master flow, ownership map, admissible-case algebra, and invariants. Numbering is stable scope identity, not total execution order.

Dependency graph:

```text
Track A — cleanup:
  Phase 2
  depends on: Phase 0 only

Track B — qualification baseline:
  Phase 1 -> Phase 3

Track C — feedback capture:
  Phase 4
  depends on: Phase 0 star semantics, stable job identity, existing immutable ranking artifact
  may proceed in parallel with Tracks A and B

Track D — preference learning:
  Phase 4 -> Phase 5
  Phase 3 + Phase 5 -> Phase 6 -> Phase 7
```

Later scopes may inspect earlier artifacts, but they may not create second owner for earlier truth. Ranking-contract changes create new compatible cohorts rather than rewriting existing rating evidence.

### Phase 0: approve ownership and seven child-spec scopes

**Purpose:**
- close authority, sequence, replacement, and dependency questions before code changes

**Steps:**
1. approve this master specification as parent design authority
2. confirm seven child-spec scopes and target files
3. confirm `config/policy/eligibility.yaml`, `config/policy/ranking.yaml`, and `config/policy/decision_learning.yaml` as separate numeric-policy owners
4. confirm enriched job facts, immutable ranking artifacts, and SQLite ledgers as canonical evidence layers
5. confirm BM25/BM25F surfaces are replacement targets, not dormant future architecture
6. confirm learned policy is only bounded latent residual over fixed baseline
7. record deliberate deferral as named non-goal, not implicit branch

**Verification:**
- every mutable semantic fact has one named owner
- every generated or derived fact identifies upstream owner
- no child spec owns another child spec's canonical fact
- replacement map names old surfaces and successor contracts

**Exit Criteria:**
- master spec is approved
- seven-child-spec dependency graph is approved
- each implementation track remains blocked only until its own prerequisites and child spec are approved

### Phase 1: add location and language facts, evaluators, normalization, and eligibility policy

**Child spec:**
- `docs/superpowers/specs/2026-07-15-16-40-fitcv-inverse-optimization-phase-1-location-language-eligibility-spec.md`

**Purpose:**
- make actual location and required language first-class, versioned ranking inputs with uniform soft and hard policy behavior

**Primary targets:**
- `config/policy/eligibility.yaml`
- `src/fitcv/ingest.py`
- `src/fitcv/normalize.py`
- `src/fitcv/enrich.py`
- `src/fitcv/fit_factors.py`
- `src/fitcv/rule_filter.py`
- `src/fitcv/config.py`
- `src/fitcv/pipeline.py`
- `src/fitcv/pipeline_stage_runner.py`
- `src/fitcv_cp/sqlite_store.py`
- `docs/stages/normalize.source.yaml`
- `docs/stages/enrich.source.yaml`
- `docs/stages/rule_filter.source.yaml`
- `tests/test_normalize.py`
- `tests/test_ingest.py`
- `tests/test_enrich.py`
- `tests/test_rule_filter.py`
- `tests/test_pipeline.py`
- `tests/test_pipeline_stage_resume_parity.py`
- `tests/test_fitcv_cp/test_sqlite_store.py`

**Steps:**
1. adapt provider-native location fields once at ingest boundary, preserve current work-mode field, and add separate canonical actual-location fact
2. extract actual city, region, country, remote scope, source evidence, and extraction status without overwriting raw text
3. extract zero or more language requirements with language, expected level, requirement type, source evidence, and extraction status
4. define one evaluator result schema for location and language while keeping factor-specific evaluators and missing semantics
5. define `disabled`, `ranking_only`, and `gate_required` projections in `config/policy/eligibility.yaml`
6. reject confirmed hard-constraint failures in `rule_filter`; retain unknown with diagnostic
7. build score-normalization inputs only from post-gate eligible jobs so rejected jobs cannot distort ranking normalization
8. keep normalizer formulas globally stable, versioned, and independent of current batch extrema
9. emit `ranking_enabled` so Phase 3 can derive policy-level effective weights once; never renormalize weights per job
10. persist raw fact, normalized evaluator result, policy projection, reason code, evidence, and versions

**Verification:**
- work mode and actual location remain distinct fields
- location and language use same result envelope and policy projection path
- hard-gated confirmed failure is excluded before score normalization and shortlist
- unknown does not fail hard gate and receives factor-specific diagnostic handling
- identical input under same policy and normalizer versions produces identical normalized value across runs and cohorts
- hard-gated or disabled factors expose `ranking_enabled: false`; ranking-only factors expose `true`
- no per-job or post-missing weight renormalization exists

**Exit Criteria:**
- actual location and language facts are durable SSOT inputs
- soft and hard modes work through one policy algebra
- eligible-set normalization boundary is explicit and versioned
### Phase 2: remove BM25/BM25F and make shortlist vector-only

**Purpose:**
- delete unused lexical scaffolding and make actual retrieval behavior match documented architecture

**Primary targets:**
- `config/shortlist_lexical.yaml`
- `src/fitcv/config.py`
- `src/fitcv/vector_search.py`
- `src/fitcv/pipeline.py`
- `docs/stages/shortlist.source.yaml`
- `tests/test_vector_search.py`
- `tests/test_pipeline.py`
- `docs/superpowers/specs/2026-05-28-14-09-shortlist-hybrid-retrieval-spec.md`
- `docs/superpowers/specs/2026-05-28-16-14-shortlist-bm25-upgrade-spec.md`
- `docs/superpowers/plans/2026-05-28-14-14-shortlist-hybrid-retrieval-plan.md`
- `docs/superpowers/plans/2026-05-28-16-18-shortlist-bm25-upgrade-plan.md`

**Steps:**
1. confirm current production shortlist sorts cosine similarity and does not execute BM25, BM25F, RRF, or hybrid rank fusion
2. define vector-only contract as `eligible jobs -> vector_similarity -> vector_rank -> Top N`
3. preserve `job_url`, `vector_similarity`, `vector_rank`, and `shortlist_origin` as retrieval evidence
4. delete `config/shortlist_lexical.yaml` and its loader entry
5. delete lexical query-payload helpers and protected-term/formula hashes from `src/fitcv/vector_search.py`
6. delete pipeline debug construction and output fields that imply lexical or hybrid runtime ranking
7. remove BM25/BM25F-specific tests; retain vector retrieval, deterministic tie, and row-contract tests
8. mark prior lexical-upgrade specs/plans `superseded` through planning lifecycle instead of silently deleting history
9. add bounded deterministic audit/exploration sample below production cutoff for retrieval recall inspection

**Verification:**
- source search finds no active BM25, BM25F, RRF, hybrid formula, protected-term payload, or lexical config owner
- vector shortlist ordering remains deterministic under same embedding evidence
- shortlist artifact contains only truthful vector-retrieval fields
- audit sample is bounded, reproducible, and excluded from production ranking unless selected by normal shortlist rule
- planning lifecycle accepts superseded lexical artifacts

**Exit Criteria:**
- runtime, config, tests, docs, and artifact labels agree on vector-only retrieval
- no dormant lexical surface remains as competing architecture
### Phase 3: establish ranking-v2 fixed baseline, stable normalization, and downstream labels

**Purpose:**
- replace overlapping and unstable score composition with one explicit baseline contract before learning preferences

**Primary targets:**
- `config/policy/ranking.yaml`
- `config/policy/decision_learning.yaml`
- `src/fitcv/config.py`
- `src/fitcv/ranking_contract.py`
- `src/fitcv/ranking.py`
- `src/fitcv/ai_score.py`
- `src/fitcv/agentic_cv_analysis.py`
- `src/fitcv_cp/settings_schema.py`
- `docs/stages/ranking.source.yaml`
- `docs/stages/cv_analysis.source.yaml`
- `tests/test_ranking.py`
- `tests/test_ai_score.py`
- `tests/test_pipeline.py`

**Steps:**
1. inventory production ranking weights, thresholds, subweights, fallback defaults, score labels, and normalization versions
2. map raw `ai_score` once to `holistic_ai_fit`; do not duplicate AI subdimensions as independent structured factors
3. define fixed structured factors: `must_have_match`, `title_relevance`, `seniority_fit`, `declared_preference_fit`, `location_fit`, and `language_fit`
4. keep `vector_similarity` and `vector_rank` as retrieval evidence only
5. move all mutable baseline numeric values to `config/policy/ranking.yaml`; keep factor semantics and validation in code
6. compute `structured_fit`, `baseline_fit`, and `baseline_fit_label` through one ranking contract
7. version every factor normalizer and baseline score contract; forbid cohort-relative min-max scaling
8. prevent overlap through documented factor ownership, contribution reporting, and fixed channel weights
9. rename ambiguous `preference_fit` surfaces to `declared_preference_fit`; reserve learned preference naming for latent residual only
10. make downstream `strong`, `stretch`, and `skip` consume persisted `baseline_fit_label`; fallback derives label from `baseline_fit`, never personalized score
11. define `learned_alpha`, vector norm bound, optimizer, solver, evaluation, and activation policy in `config/policy/decision_learning.yaml`
12. derive effective structured-factor weights once from eligibility modes and fingerprint them in ranking contract
13. run mandatory baseline ablation: current holistic AI only, structured only, proposed combined baseline
14. produce old-label to new-label migration matrix and enforce approved migration limits before combined baseline promotion
15. emit canonical contract payloads and fingerprints from validated values

**Verification:**
- one baseline numeric owner and one decision-learning numeric owner exist
- config validation rejects unknown factors, missing weights, invalid fixed sums, invalid thresholds, nonpositive regularization, invalid alpha, unsupported solver, and embedding mismatch
- AI contribution appears once in baseline composition
- vector similarity never contributes to baseline or personalized score except through normalized embedding residual
- combined baseline improves approved qualification benchmark and stays inside approved label-migration limits, or current holistic AI baseline remains authoritative
- effective structured weights sum to one across ranking-only factors and stay fixed for every job in same policy context
- baseline labels remain unchanged when latent residual changes ordering
- identical factor values under same normalizer and policy versions produce same baseline score globally

**Exit Criteria:**
- fixed baseline is explicit, versioned, and reproducible
- downstream CV gates depend on baseline label only
- learned preference has one isolated residual seam
### Phase 4: add decision episodes, rating ledger, and native 1–5-star UI

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
2. materialize one episode from one compatible ranking artifact, stable preference context, qualification context, and versioned personal-application-interest scale
3. use `raw_job_fingerprint` as `alternative_id`; preserve URL only as metadata
4. derive `episode_id` from canonical Layer 4 payload and freeze baseline, label, embedding, qualification context, preference context, rating-scale, and policy fingerprints
5. add `set_rating` and `clear_rating` POST operations with redirect-after-POST
6. render accessible native 1–5 controls with HTML and CSS; require no JavaScript
7. validate form data and redirect targets at HTTP boundary
8. keep GET routes read-only
9. preserve unrated as unknown and show effective rating derived from ledger
10. verify `ControlPlaneStore` delegation and SQLite persistence; future backend fails explicitly until same contract exists
11. keep application-status history in separate ledger and never infer application from rating

**Verification:**
- repeated rating changes append events and produce one deterministic effective value
- clear appends event and returns effective state to unrated
- invalid ratings, unknown alternatives, incompatible episodes, and unsafe redirects are rejected
- first rating plus episode materialization is atomic
- historical embedding evidence is copied, fingerprinted, and never recomputed
- no historical application or rating record is synthesized

**Exit Criteria:**
- user can rate any displayed admissible alternative repeatedly
- raw rating evidence is durable, replayable, and independent of optimization availability
### Phase 5: add effective reducer and symmetric preference compiler

**Purpose:**
- translate low-friction ordinal evidence into one deterministic comparison algebra

**Primary targets:**
- `src/fitcv/decision_feedback.py`
- `tests/test_decision_feedback.py`

**Steps:**
1. define immutable rating, effective-state, preference-edge, diagnostic, and compiler-result records
2. reduce events by `(created_at, event_id)` through one shared query or reducer
3. validate episode, scale, ranking, embedding, baseline, profile, and compiler compatibility before pairing
4. enumerate each unordered pair exactly once
5. orient qualifying pairs from higher rating to lower rating
6. omit unrated, equal, and below-gap pairs without inventing constraints
7. apply configured rating-gap evidence weight
8. cap total episode influence without forcing episode weight sum to one
9. preserve exactly two effective source event IDs, compiler version, and deterministic edge ordering
10. fingerprint canonical compiler input and output

**Verification:**
- exhaustive table-driven tests cover every pair in `{unrated,1,2,3,4,5} x {unrated,1,2,3,4,5}`
- swapping alternatives swaps edge orientation and preserves weight
- permuting input row order preserves canonical output and fingerprint
- compiling twice from same watermark produces byte-equivalent canonical output
- zero-edge episodes return valid `insufficient_evidence`
- one-edge episodes preserve configured gap-weight ordering

**Exit Criteria:**
- UI representation no longer matters after boundary adaptation
- every admissible rating case follows one reducer and one compiler path
### Phase 6: add CVXPY latent-residual solver and episode-grouped evaluation

**Purpose:**
- learn smallest bounded latent correction supported by ratings while fixed baseline remains unchanged

**Primary targets:**
- `src/fitcv/inverse_optimization.py`
- `scripts/run_inverse_optimization.py`
- `tests/test_inverse_optimization.py`
- optional offline dependency declaration verified by child spec

**Steps:**
1. define plain immutable solver-input and solver-result records
2. load all events through watermark, reduce complete effective state, and rebuild complete compatible edge set
3. validate finite baseline scores, normalized embeddings, dimensions, fingerprints, alpha, margin, regularization, and deterministic edge order before CVXPY construction
4. set prior preference vector to zero; active parent remains comparison/lifecycle reference only
5. model baseline score difference plus fixed-alpha embedding residual for every directed edge
6. add nonnegative per-edge slack and one unit-L2-norm bound on preference vector
7. use one explicit supported solver and deterministic option set
8. reject unsupported statuses and independently recompute vector norm and preference residuals
9. split evaluation by episode, never edge
10. compare candidate against zero-residual baseline and compatible active parent on held-out pair agreement, violations, weighted regret, vector stability, and display-clipping frequency
11. include bounded vector-shortlist audit metrics and coverage by baseline label, rating gap, location, and language
12. return diagnostics for weak or collinear latent evidence without deleting evidence
13. expose `train` and `evaluate` through one standard-library `argparse` script

**Verification:**
- synthetic recoverable case moves latent vector toward known embedding direction
- zero useful direction returns zero-centered or no-op result
- contradictory case remains feasible through slack
- invalid dimension, alpha, regularization, or embedding contract fails before solver call
- row and edge permutations preserve result within configured numeric tolerance
- grouped evaluation never places edges from one episode in both train and validation
- runtime baseline ranking works when offline solver extras are absent

**Exit Criteria:**
- training produces typed noncandidate result or one fully evidenced latent-vector candidate
- fixed baseline weights never enter solver variables
- solver objects never cross application boundary

### Phase 7: add policy payloads, activation, runtime residual, observability, docs, and deletion

**Purpose:**
- promote compatible latent policy safely, preserve downstream labels, expose behavior, and remove superseded truth

**Primary targets:**
- `src/fitcv_cp/store.py`
- `src/fitcv_cp/sqlite_store.py`
- `src/fitcv/pipeline.py`
- `src/fitcv/ranking.py`
- `src/fitcv/agentic_cv_analysis.py`
- `scripts/run_inverse_optimization.py`
- `docs/architecture.md`
- `docs/configuration.md`
- `docs/pipeline.md`
- `docs/stages/ranking.source.yaml`
- `docs/stages/cv_analysis.source.yaml`
- `docs/features/cv_system/feature.source.yaml`
- affected tests and generated architecture outputs

**Steps:**
1. persist immutable candidate policy payloads only after solver and evaluation gates pass
2. suppress candidate creation when preference vector equals zero or parent within configured tolerance
3. bind payload to exact baseline, ranking, embedding, alpha, evidence, compiler, optimizer, solver, and evaluation contracts
4. add explicit reject, activate, and rollback commands
5. implement transactional compare-and-swap activation against current effective parent and current fingerprints
6. enforce one active compatible payload per domain and bound contract set
7. append activation history for activate, reject, stale, retire, and rollback actions
8. resolve active payload once at run start using runtime compatibility only; solver metadata remains training provenance
9. compute residual with standard-library or runtime-native dot-product math and order by raw personalized rank score
10. persist baseline score, residual, raw rank score, clipped display score, clipping flag, payload ID, and fingerprints
11. keep `strong`, `stretch`, and `skip` derived from baseline score; learned residual changes ordering only
12. fall back visibly to zero residual on absent, incompatible, invalid, or unavailable payload storage
13. expose factor, eligibility, retrieval-audit, rating, edge, solver, stability, clipping, staleness, and active-payload diagnostics
14. update human-owned feature and stage source files first, then regenerate managed architecture outputs
15. delete obsolete numeric defaults, BM25/BM25F surfaces, shadow state, weight-learning language, dead adapters, and temporary migration paths
16. define shared domain adapter only when second concrete decision domain proves common shape

**Verification:**
- stale candidate cannot activate after any bound contract or evidence change
- concurrent activation leaves one winner and one explicit conflict
- rollback restores exact prior vector and appends auditable transition
- old runs retain original baseline, embedding, vector, and score evidence after later activation
- runtime imports no CVXPY and no NumPy solely for dot product
- baseline labels and downstream CV gates stay unchanged when learned ordering changes
- docs point to canonical owners and generated outputs are synchronized
- deletion search finds no active BM25/BM25F or learned-baseline-weight owner

**Exit Criteria:**
- activation is manual, transactional, reproducible, and reversible
- runtime behavior is solver-independent and downstream-label stable
- system is inspectable and source-first
- no speculative plugin framework or competing truth remains
## Design Decisions

### Decision: ordinal stars remain evidence SSOT

- context: stars are easy to provide but do not define cardinal utility distances
- choice: define stars as personal application interest after eligibility, persist raw 1–5 labels and clear events, and derive ordering only from configured clear gaps
- alternatives considered:
  - repeatedly ask explicit pairwise questions
  - convert stars directly into numeric utility targets
- impact:
  - user interaction stays low-friction
  - qualification remains owned by baseline fit rather than being relearned through ambiguous rating meaning
  - equal ratings and one-star gaps create no forced ordering in first policy

### Decision: raw personalized score owns ordering

- context: clipping raw scores to `[0,1]` can erase trained margins and create artificial ties
- choice: use raw personalized score for ordering and pairwise evaluation; use clipped display score only for UI compatibility
- alternatives considered:
  - rank by clipped score
- impact:
  - runtime ordering matches convex training objective
  - clipping remains observable without changing rank

### Decision: one symmetric pair compiler handles all rating cases

- context: case-specific solver branches create drift and asymmetry
- choice: enumerate unordered pairs once, orient only qualifying unequal pairs, then emit one edge type
- alternatives considered:
  - separate rules for star combinations
  - transitive reduction before optimization
- impact:
  - all admissible cases share one algebra
  - permutation and swap properties become directly testable

### Decision: location and language share one factor envelope, not one meaning

- context: both factors need uniform policy handling, but missing location and missing language are not semantically identical
- choice: reuse one evaluator-result and policy-projection schema while keeping factor-specific extraction, normalization, evidence, and unknown mappings
- alternatives considered:
  - special-case pipeline branches for each factor
  - one universal missing-value score
- impact:
  - hard and soft modes remain symmetric
  - factor semantics remain correct without duplicated lifecycle code

### Decision: vector retrieval replaces unused lexical scaffolding

- context: runtime shortlist is cosine-only while config and debug surfaces imply BM25/BM25F behavior that does not exist
- choice: delete lexical and hybrid claims, preserve vector evidence, and measure recall through bounded deterministic audit sampling
- alternatives considered:
  - keep dormant BM25/BM25F config for future use
  - implement hybrid retrieval without measured need
- impact:
  - architecture matches runtime truth
  - another retrieval channel requires new evidence and approved spec

### Decision: fixed baseline plus bounded latent residual

- context: learning six visible factor weights would destabilize explicit semantics and amplify overlap with holistic AI score
- choice: keep baseline weights fixed and learn only zero-centered unit-bounded preference vector over normalized job embeddings with fixed small alpha
- alternatives considered:
  - relearn baseline factor weights
  - treat star labels as direct score targets
- impact:
  - explicit factors remain auditable
  - learned behavior changes ordering without redefining score bands

### Decision: baseline promotion requires ablation and label-migration proof

- context: holistic AI score and structured factors overlap semantically
- choice: compare AI-only, structured-only, and combined baselines; promote combined baseline only after benchmark improvement and bounded label migration
- alternatives considered:
  - accept combined baseline from contribution visibility alone
  - discard structured factors without measurement
- impact:
  - downstream CV eligibility cannot drift silently
  - AI-only baseline remains safe fallback when combined baseline fails gate

### Decision: hard-gate weight removal is normalized once per policy

- context: zeroing hard-gated factor without redistribution changes structured-score scale
- choice: normalize configured weights over ranking-only factors once at policy load and fingerprint effective weights
- alternatives considered:
  - leave total weight below one
  - renormalize per job
- impact:
  - score scale stays stable within policy context
  - missing values cannot change weights job by job

### Decision: immutable baseline and embedding evidence freeze decision context

- context: recomputing old baseline scores or embeddings under new code would rewrite historical evidence
- choice: copy exact baseline score, label, normalized embedding, vector fingerprint, and contract fingerprints from ranking artifact into episode alternatives
- alternatives considered:
  - recompute from current job data
  - store only job ID and query current features
- impact:
  - training is replayable
  - ranking-contract and embedding-contract changes form separate cohorts

### Decision: configuration owns numeric policy; code owns semantics

- context: eligibility, baseline, and learning defaults can drift across config, Python, settings, and tests
- choice: three named YAML policy files own their numeric domains; code owns admissible names, types, direction, ranges, and validation
- alternatives considered:
  - hard-code all defaults
  - make config define executable feature semantics
- impact:
  - one owner exists for each numeric policy domain without turning config into code

### Decision: maintained convex solver stays offline

- context: project needs reliable inverse optimization, not a custom numerical library or runtime dependency
- choice: model convex latent-residual problem in CVXPY with one explicit conic-capable supported solver inside offline module
- alternatives considered:
  - hand-written optimizer
  - solver calls during ranking
- impact:
  - native solver behavior is reused
  - rating capture and runtime ranking remain available without solver stack

### Decision: evidence cohorts are compatibility-bound

- context: mixed ranking contracts, embedding contracts, profiles, or rating scales make one optimization problem semantically invalid
- choice: train only compatible cohorts and reject mixed inputs before matrix construction
- alternatives considered:
  - silently align missing dimensions
  - coerce old scales into current scale
- impact:
  - invalid cases fail uniformly at boundary
  - migration requires an explicit versioned adapter and new evidence fingerprint

### Decision: training is full refit from zero

- context: incremental events with zero prior would forget older preferences
- choice: rebuild complete effective edge set through event watermark and fit from zero; parent remains evaluation and lifecycle reference
- alternatives considered:
  - fit only new events from zero
  - regularize incrementally toward active parent
- impact:
  - replay stays deterministic
  - first implementation avoids incremental-learning state

### Decision: policy activation is separate from training

- context: optimization success alone does not prove business safety or freshness
- choice: create immutable candidates, evaluate them, then require manual transactional activation
- alternatives considered:
  - overwrite ranking config
  - auto-activate every optimal result
- impact:
  - active policy remains stable on failure
  - rollback and audit remain exact

### Decision: counts gate work but do not prove stable latent direction

- context: many correlated edges may still provide little independent embedding-direction information
- choice: use episode counts as prerequisites and require held-out, resample, vector-stability, norm, and clipping diagnostics
- alternatives considered:
  - activate after a fixed edge count
- impact:
  - weak latent candidates remain visible but cannot pass stability gates accidentally

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

### Decision: child scopes form dependency graph, not release train

- context: cleanup, feedback capture, baseline redesign, and learning have different prerequisites
- choice: retain one parent architecture while allowing BM25 cleanup, feedback capture, and baseline work to proceed on independent approved tracks
- alternatives considered:
  - require strict Phase 1 through Phase 7 implementation order
- impact:
  - rating evidence can begin earlier
  - contract changes create new cohorts rather than rewriting evidence

## Reuse Contract and Future Components

Reusable structure is:

`ImmutableContext -> AppendOnlyEvidence -> EffectiveState -> SymmetricRelations -> BoundedResidualOptimization -> CandidatePolicyPayload -> GroupedEvaluation -> ActivationLedger`

Shared infrastructure may own IDs, canonical JSON, fingerprints, append-only event mechanics, deterministic reduction, pair enumeration, solver result envelopes, evaluation grouping, immutable policy payloads, lifecycle transitions, compare-and-swap activation, rollback, and observability envelopes.

Each domain must separately own alternative identity rules, context contracts, evidence scale semantics, relation compiler policy, feasible set, objective meaning, evaluation gates, and active policy. Learned vectors, parameters, and evidence never cross domains.

Components that may reuse this structure:

- **application history:** append `application_status` events against stable job identity; never infer application from a rating
- **active-learning job selection:** choose which unrated jobs would reduce uncertainty most, while rating UI remains unchanged
- **counterfactual explanation:** show smallest baseline fact or latent-residual change needed to reverse one ranking relation
- **preference drift:** compare time-grouped candidate policy payloads without rewriting old evidence
- **what-if simulator:** evaluate hypothetical fixed policies, gates, alpha values, or residual vectors without creating or activating a payload
- **uncertainty report:** expose weak latent directions, clipping, retrieval coverage, and evidence coverage
- **threshold or subweight calibration:** reuse lifecycle with a new domain-specific feasible set and evaluation contract
- **shortlist or retrieval tuning:** learn bounded policy from ratings while preserving retrieval-specific feature semantics
- **soft-filter calibration:** treat filter outcomes as alternatives or policy actions only after a dedicated evidence contract exists
- **synonym proposal ratings:** rate normalized skill or title proposals and learn proposal policy in an isolated domain
- **CV evidence or draft ratings:** learn evidence-selection or drafting preferences without sharing ranking vectors
- **provider routing:** learn bounded routing policy from explicit outcome evidence
- **job-source allocation:** learn source budgets under source-specific constraints

A new component may reuse generic lifecycle code only when it supplies all domain-owned contracts and passes the same admissibility, determinism, replay, evaluation, staleness, and activation tests. Similar table shape alone is not enough reason to share semantics.

## Invariants

1. Raw actual-location and language evidence is preserved; normalized facts never overwrite source text.
2. Work mode and actual job location are separate canonical facts.
3. Location and language share evaluator and policy-result shapes, not factor-specific semantics.
4. `gate_required` rejects confirmed failure only; unknown remains admissible with diagnostic.
5. Disabled and hard-gated factors carry zero effective weight; ranking-only weights are normalized once per policy context and never per job.
6. Rejected jobs are excluded before score-normalization inputs and shortlist construction.
7. Normalizer behavior is globally stable and versioned; current batch extrema cannot change same input's normalized value.
8. BM25, BM25F, RRF, protected-term payloads, and hybrid-retrieval claims have no active runtime, config, or artifact owner.
9. `vector_similarity` and `vector_rank` are retrieval evidence, not baseline ranking factors.
10. Fixed structured factors are exactly `must_have_match`, `title_relevance`, `seniority_fit`, `declared_preference_fit`, `location_fit`, and `language_fit` for ranking-v2.
11. Holistic AI contribution enters baseline composition once as `holistic_ai_fit`.
12. Baseline numeric ranking policy exists only in `config/policy/ranking.yaml`.
13. Eligibility numeric policy exists only in `config/policy/eligibility.yaml`.
14. Decision-learning numeric policy exists only in `config/policy/decision_learning.yaml`.
15. Code owns executable semantics and admissible schemas; config cannot define feature logic.
16. Raw personalized score owns ordering and pairwise evaluation; clipped personalized score is display-only.
17. `strong`, `stretch`, and `skip` derive from `baseline_fit`; latent residual changes ordering only in first implementation.
18. Star ratings mean personal application interest after eligibility, not qualification or recorded application status.
19. Raw rating events are append-only user-evidence SSOT.
20. Effective ratings are derived; no mutable current-rating shadow owner exists.
21. Unrated means unknown, not neutral, zero, disliked, or missing-at-random.
22. Equal ratings create no equality or preference constraint.
23. Only rating gaps meeting versioned policy create one directed edge.
24. Swapping alternatives reverses edge direction and preserves edge weight.
25. Capped episode budgeting preserves configured rating-gap weight ordering while bounding total episode influence.
26. Input ordering cannot change canonical edge set, fingerprints, solver problem, or policy result beyond declared numeric tolerance.
27. Every compiled edge references exactly two effective source events; full history remains in ledger through watermark.
28. Episode alternatives use stable `raw_job_fingerprint`; mutable URLs never become primary identity.
29. Episode ID, persistence identity, lookup, and idempotency use one canonical episode payload.
30. Historical baseline scores, labels, normalized embeddings, and vector fingerprints come from immutable ranking artifacts and are never recomputed in place.
31. One training cohort contains one compatible domain, rating scale, preference context, ranking contract, baseline policy, and embedding contract; qualification context remains frozen per episode.
32. Training full-refits from zero over complete effective evidence through watermark; parent vector is not optimization prior.
33. Solver receives only validated finite baseline scores, normalized embeddings, valid dimensions, fixed alpha, positive regularization, and canonical edge order.
34. Solver variables contain latent preference vector and slack only; fixed baseline factor weights are never learned.
35. Learned preference vector remains inside configured L2 bound; independent post-solver validation recomputes norm and preference residuals.
36. Contradictory admissible evidence remains feasible through nonnegative slack.
37. Training never mutates baseline config or active policy.
38. Candidate policy payloads are immutable and bind exact baseline, ranking, embedding, alpha, parent, evidence, compiler, optimizer, solver, and evaluation fingerprints.
39. Activation and rollback are transactional compare-and-swap operations with append-only history.
40. At most one compatible active payload exists per domain and runtime contract set.
41. Training-provenance changes may stale candidates but cannot invalidate active payload when runtime compatibility remains satisfied.
42. Old runs retain exact baseline, embedding, residual, raw rank score, display score, label, and policy identity after future activations.
43. Runtime ranking never imports or invokes CVXPY; NumPy is not added solely for dot-product math.
44. Missing, incompatible, invalid, or unavailable learned policy falls back visibly to zero residual over validated baseline.
45. Application history and rating history are separate facts; neither is inferred from other.
46. Shared infrastructure never shares domain evidence, learned vectors, semantic parameters, or activation authority across domains.
47. Generated documentation is updated from human-owned sources, never hand-edited as authority.
## Acceptance Criteria

- one ownership table maps every canonical and derived fact to one owner
- actual location, work mode, and language requirements persist as distinct evidence-backed facts
- location and language pass same evaluator/policy interfaces across disabled, ranking-only, hard-gate, unknown, and not-applicable cases
- confirmed hard failures are removed before normalization inputs and shortlist; unknown cases remain visible with diagnostics
- stable versioned normalizers produce same value for same input independent of cohort composition
- active source, config, tests, docs, and artifacts contain no BM25/BM25F or hybrid-runtime claim
- vector-only shortlist preserves deterministic ordering and bounded audit sample
- ranking-v2 composes one holistic AI channel plus six fixed structured factors without vector-score leakage
- ranking-v2 promotion requires AI-only, structured-only, and combined ablation plus bounded `strong|stretch|skip` migration; failed gate retains AI-only baseline authority
- disabled and hard-gated factors have zero effective weight, while ranking-only effective weights normalize once per policy context and stay identical for every job in that context
- downstream `strong`, `stretch`, and `skip` remain baseline-derived under personalized ordering
- 1–5-star interactions persist exact ordinal personal-application-interest labels after eligibility and support clear without JavaScript
- exhaustive rating-pair tests prove uniform compiler behavior
- property tests prove swap symmetry, permutation invariance, deterministic replay, preserved rating-gap weight ordering, and capped episode influence
- every training run full-refits from zero over complete effective evidence through its watermark; no v1 incremental window exists
- one canonical episode payload drives episode ID, database uniqueness, lookup, materialization idempotency, and fingerprint tests
- solver tests prove fixed baseline weights, zero-centered bounded vector, contradiction feasibility, boundary rejection, and independent residual validation
- evaluation tests prove episode-group separation, zero-residual comparison, vector stability, raw-score ordering, display-only clipping reporting, and retrieval-audit coverage
- policy-payload tests prove complete Layer 11 provenance persistence, payload immutability, lifecycle compatibility, no-op suppression, staleness, one-active enforcement, concurrent activation safety, and rollback
- runtime tests prove zero-residual fallback, raw-score ordering, persisted raw/display score evidence, baseline-label stability, runtime-only compatibility, and absence of offline solver imports
- store-boundary and SQLite tests prove no owned production path silently loses evidence or lifecycle events
- docs and config reference canonical owners rather than copied mutable values
- no implementation phase begins before its child spec is approved

## Non-Goals

- reconstruct past applications, ratings, or preferences that were never recorded
- infer application from viewing, rating, shortlisting, or ranking job
- replace 1–5 stars with repeated mandatory pairwise questions
- treat ordinal stars as cardinal utility values
- learn from equal ratings or below-gap ratings in first implementation
- train incrementally from only events added after previous watermark in first implementation
- relearn fixed baseline factor weights
- let latent residual change `strong`, `stretch`, or `skip` in first implementation
- rank or evaluate pairs by clipped `personalized_display_score`
- implement BM25, BM25F, RRF, or hybrid retrieval without measured vector-recall need and separate approved spec
- optimize thresholds, subweights, hard-gate policy, retrieval policy, providers, or source allocation in ranking latent-residual solver
- personalize per session, device, or anonymous viewer
- mix users, preference contexts, ranking contracts, embedding contracts, rating scales, or domains in one cohort
- auto-activate learned policy
- call optimizer in request handling or runtime ranking
- add ORM, migration framework, UI state framework, custom optimizer, matrix DSL, CLI framework, event bus, plugin framework, or custom dot-product abstraction
- recompute mutable embeddings or baseline scores into historical episodes
- expose private operating-system artifacts through public mirror

## Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| location field still conflates work mode and city | separate schema fields, extraction evidence, migration tests, and stage-contract checks |
| language/location extraction is uncertain | preserve raw evidence, status, confidence, reason code, and unknown path |
| hard gate removes useful jobs or distorts score normalization | reject confirmed failure only; build normalization inputs after gate; audit retained/rejected counts |
| missing semantics become universal defaults | keep factor-specific policy mappings and tests for every status |
| AI score overlaps structured factors | require AI-only, structured-only, and combined ablation plus qualification improvement and bounded label migration; retain AI-only authority when combined gate fails |
| vector similarity leaks into final score | contract and source-search gates keep it retrieval-only |
| vector-only shortlist misses relevant jobs | bounded deterministic below-cutoff audit sample and recall review before adding retrieval channel |
| dormant BM25/BM25F truth survives | explicit deletion phase across config, loader, helpers, debug outputs, tests, docs, specs, and plans |
| users interpret stars as qualification, application status, or generic quality | label scale as personal application interest after eligibility, version semantics, keep application ledger separate, and retain raw events |
| pair explosion within large episodes | bound reviewed set; deterministic combinations; add materialized-edge cache only after measured need |
| one episode dominates through many pairs | apply capped episode evidence budget without forcing sum-to-one normalization or erasing configured gap ordering |
| edge correlation inflates evaluation | split and resample by episode, never edge |
| weak latent direction looks confident | require held-out, resample, vector-norm, stability, clipping, and coverage diagnostics |
| contradictory evidence makes hard preference constraints fail | use nonnegative slack and retain contradiction diagnostics |
| latent residual dominates baseline | fixed small alpha, unit vector bound, clipping metric, and activation gate |
| mutable URLs split identity | use `raw_job_fingerprint`; URL remains metadata |
| episode ID, uniqueness, lookup, and idempotency drift apart | derive all four from one canonical episode payload and test exact payload equality |
| old embeddings drift under new model | freeze normalized vectors, model identity, dimensions, and fingerprints |
| incremental window forgets older effective preferences | full-refit from zero over all effective evidence through watermark; defer parent-centered incremental training |
| stale candidate overwrites newer truth | transactional parent and all-contract fingerprint compare-and-swap |
| training-tool version change disables valid active vector | separate training-provenance staleness from runtime compatibility; active payload needs only materialized runtime contracts |
| solver package breaks runtime | offline module boundary and runtime import test |
| persistence outage creates hidden state | zero-residual baseline fallback; no memory-only active policy |
| future backend silently omits feedback | explicit unsupported error until contract tests exist |
| generic abstraction leaks ranking semantics | delay shared protocol until second concrete domain |
| generated docs drift | edit source YAML first; run architecture sync check |
| ratings mistaken for application history | separate ledgers and UI labels; never infer either fact |
## Validation Plan

- proof target: planning artifact follows repo lifecycle
  - method: run `python scripts/validate_planning_lifecycle.py`
  - evidence: spec passes required frontmatter, section, parent-thread, status, and target validation
- proof target: architecture documentation stays source-first
  - method: run `python tools/docs/generate_architecture_metadata.py --check`; use `scripts/sync_architecture_docs.py --check` only in repo roles that provide that adapter
  - evidence: generated feature, stage, lineage, and discovery outputs match human-owned sources
- proof target: repo contracts remain valid
  - method: run `python scripts/hooks/run_validator.py --fast` and `python scripts/validate_repo_contracts.py --fast`
  - evidence: canonical fast validators pass
- proof target: location and language facts remain distinct, versioned, and uniformly projected
  - method: schema, extraction, evaluator, eligibility, and stage-contract tests across every status and policy mode
  - evidence: actual location, work mode, and language requirements retain separate evidence and deterministic outcomes
- proof target: hard constraints affect normalization boundary correctly
  - method: pipeline tests with pass, fail, unknown, and not-applicable jobs under ranking-only and gate-required modes
  - evidence: confirmed failures are excluded before normalization inputs and shortlist; retained job scores remain stable
- proof target: score normalization is globally stable
  - method: repeat same factor inputs across different batch compositions under same policy version
  - evidence: normalized factor and baseline values are identical
- proof target: BM25/BM25F removal is complete
  - method: source search plus focused config, vector-search, pipeline, test, doc, spec, and plan inspection
  - evidence: no active lexical config, loader, helper, debug payload, test expectation, or hybrid claim remains
- proof target: vector-only retrieval remains observable
  - method: focused vector-search and pipeline tests plus deterministic below-cutoff audit fixture
  - evidence: vector ordering, ranks, row contract, cutoff behavior, and audit sample are reproducible
- proof target: baseline composition avoids channel leakage
  - method: focused ranking tests with isolated changes to holistic, structured, vector, location, and language inputs plus AI-only, structured-only, and combined benchmark ablation
  - evidence: AI contributes once, six structured factors contribute through fixed weights, vector evidence does not enter baseline score, and combined baseline activates only after qualification gain with bounded label migration
- proof target: policy-level effective weights are stable
  - method: load disabled, ranking-only, and gate-required factor combinations; compare all retained jobs under one policy context and repeat across different cohorts
  - evidence: disabled and hard-gated weights are zero, ranking-only weights sum to one once per context, and effective-weight fingerprint is cohort-independent
- proof target: downstream labels remain baseline-derived
  - method: construct jobs whose learned residual reverses order without crossing baseline inputs
  - evidence: personalized ordering changes while persisted `strong|stretch|skip` labels and CV gate stay unchanged
- proof target: rating persistence is append-only and replayable
  - method: store-boundary, SQLite, and HTTP tests for set, change, clear, invalid input, and atomic first write
  - evidence: event sequence deterministically reduces to expected effective state with no update-in-place path
- proof target: star semantics remain unambiguous
  - method: schema, UI-copy, API, config, and artifact assertions for all five labels plus clear/unrated state
  - evidence: every surface defines stars as personal application interest after eligibility and never as qualification or application status
- proof target: compiler is uniform and symmetric
  - method: exhaustive 36-state pair matrix plus swap, permutation, and repeatability tests
  - evidence: only configured clear gaps emit one correctly oriented edge; capped episode budgeting preserves configured gap-weight ordering
- proof target: training window preserves complete current evidence
  - method: replay multiple training watermarks with older ratings, replacements, clears, and newly appended events
  - evidence: each run reduces all events through watermark, rebuilds complete current edge set, and full-refits from zero without forgetting retained older preferences
- proof target: episode identity has one canonical owner
  - method: materialization, database uniqueness, lookup, retry, and permutation tests against canonical episode payload
  - evidence: same canonical payload yields same episode ID and idempotent row; any identity field change yields distinct episode
- proof target: latent optimization is bounded and independently checked
  - method: synthetic, contradictory, collinear, invalid-contract, invalid-alpha, solver-failure, and zero-direction tests
  - evidence: typed status, finite vector, norm residual, max preference violation, and fixed baseline match contract
- proof target: evaluation has no episode leakage
  - method: inspect deterministic grouped split membership in tests
  - evidence: one episode ID appears in exactly one partition per evaluation fold
- proof target: lifecycle prevents unsafe promotion and preserves complete provenance
  - method: payload-schema, candidate, no-op, stale, concurrent activation, rejection, rollback, failed-transaction, and replay tests
  - evidence: persisted payload contains full Layer 11 provenance, one compatible active payload remains, and activation ledger explains every transition
- proof target: runtime stays solver-independent and reproducible
  - method: import/runtime tests without offline extras, changed solver-provenance fixture, incompatible runtime-contract fixtures, and persisted artifact assertions
  - evidence: solver changes may stale candidates but do not disable compatible active payload; run orders by raw score and records baseline, embedding, vector, raw/display score, clipping flag, label, and policy identity
- proof target: superseded truth is deleted
  - method: source search for removed lexical surfaces, copied numeric defaults, weight-learning fields, mutable current-rating fields, and alternate active-policy registries
  - evidence: only canonical owners remain

Implementation child plans should start with focused tests, then broaden to:

```text
python -m pytest tests/test_normalize.py tests/test_enrich.py tests/test_rule_filter.py
python -m pytest tests/test_vector_search.py tests/test_pipeline.py
python -m pytest tests/test_ranking.py tests/test_ai_score.py
python -m pytest tests/test_decision_feedback.py tests/test_inverse_optimization.py
python -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_sqlite_store.py
python scripts/generate_planning_lineage.py
python tools/docs/generate_architecture_metadata.py --check
python scripts/validate_planning_lifecycle.py
python scripts/validate_repo_contracts.py
```

Exact solver installation and optional-dependency test commands belong to Phase 6 child spec after solver selection is verified against supported Python and CI platforms.

## Completion Criteria

This master specification is complete when:

1. all required sections and ownership decisions are present
2. admissible-case matrix covers location/language policy states, empty or ambiguous ratings, contradiction, incompatibility, failure, concurrency, staleness, rollback, and historical replay
3. every phase names purpose, scoped steps, verification, exit criteria, and dependency edges
4. seven required child specs are named within one dependency graph; independent tracks are not forced into strict release order
5. plan-document review returns `ready` after blocking findings are fixed
6. fast validator, planning lifecycle, architecture check, repo-contract validator, and `git diff --check` pass
7. master spec is approved for child-spec drafting

Inverse-optimization replacement is complete only when:

1. all seven child specs are approved
2. all child implementation plans are completed or explicitly dropped
3. every invariant has cited verification evidence
4. actual location and language factors are active under one versioned eligibility contract
5. BM25/BM25F surfaces and learned-baseline-weight model are deleted or lifecycle-superseded
6. fixed baseline, vector-only retrieval, latent residual, and downstream labels pass compatibility and reproducibility checks
7. active policy lifecycle passes concurrency, staleness, rollback, and historical-replay checks
8. feature and stage source docs plus generated outputs are synchronized
9. closeout follows canonical repo workflow

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `docs/operating_system/lifecycle/doc-system-lifecycle.md`
- `docs/operating_system/templates/detailed-specification-template.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
