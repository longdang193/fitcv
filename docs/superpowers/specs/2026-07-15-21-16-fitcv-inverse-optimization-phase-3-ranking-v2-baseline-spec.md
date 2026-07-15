---
layer: change
artifact_type: spec
status: active
template_id: detailed-specification
name: fitcv-inverse-optimization-phase-3-ranking-v2-baseline
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-stage-authority-contract
parent_spec: docs/superpowers/specs/2026-07-14-22-25-fitcv-inverse-optimization-master-ssot-symmetry-spec.md
targets:
  - config/policy/ranking.yaml
  - src/fitcv/config.py
  - src/fitcv/contracts.py
  - src/fitcv/ranking_contract.py
  - src/fitcv/ranking.py
  - src/fitcv/ai_score.py
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_runner.py
  - src/fitcv/pipeline_stage_context.py
  - src/fitcv/pipeline_stage_artifacts.py
  - src/fitcv/pipeline_stages/common.py
  - src/fitcv/late_stage_contract.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/app_run_support.py
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/worker_job.py
  - docs/architecture.md
  - docs/configuration.md
  - docs/pipeline.md
  - docs/stages/ranking.source.yaml
  - docs/stages/cv_analysis.source.yaml
  - docs/features/cv_system/feature.source.yaml
  - tests/test_config.py
  - tests/test_ranking.py
  - tests/test_ai_score.py
  - tests/test_pipeline.py
  - tests/test_pipeline_stage_resume_parity.py
  - tests/test_agentic_cv_analysis.py
  - tests/test_pipeline_status_registry.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_settings_schema.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_structural_contract_guardrails.py
  - tests/golden/pipeline_refactor/full_run_snapshot.json
  - tests/golden/pipeline_refactor/checkpointed_run_snapshot.json
related_features:
  - cv_system
  - inspection_debugging
  - settings_system
related_stages:
  - ranking
  - cv_analysis
---

# Detailed Spec: FitCV inverse optimization Phase 3 ranking-v2 fixed baseline

## Goal

Replace the current overlapping six-feature score with one explicit, versioned
ranking-v2 baseline before any learned preference residual exists.

Phase 3 establishes this uniform flow for every admissible ranked job:

```text
raw AI score + canonical structured factor outputs
-> absolute factor normalization
-> fixed policy-level effective weights
-> structured_fit
-> baseline_fit
-> baseline_fit_label
-> deterministic baseline ordering
```

`ai_score` maps once to `holistic_ai_fit`. Six deterministic structured factors
remain separate:

1. `must_have_match`
2. `title_relevance`
3. `seniority_fit`
4. `declared_preference_fit`
5. `location_fit`
6. `language_fit`

`vector_similarity` and `vector_rank` remain shortlist evidence only. They never
enter baseline score, label, or ranking tie-breaks.

Holistic AI score remains the only production score input at Phase 3 cutover.
Label ownership intentionally changes from model-authored `fit_label` to the
deterministic threshold mapping over `holistic_ai_fit`. Phase 3 must report old
model-label versus new threshold-label migration from available legacy rows.
Direct `strong` to `skip` crossings block cutover; missing comparable evidence
requires explicit operator acceptance rather than a false compatibility claim.

The fixed baseline creates the only future seam for inverse optimization:

```text
personalized_rank_score = baseline_fit + learned_alpha * latent_residual
```

Phase 3 defines that seam but does not add decision-learning config, collect
ratings, train a preference vector, import CVXPY, or change labels from learned
preference.

## Triage

- layer: `change`
- feature type: `REPLACE`
- parent: inverse-optimization master SSOT and symmetry specification
- dependency: Phase 1 location/language eligibility is complete
- consumed cleanup: Phase 2 vector-only shortlist is complete
- affected stages: `ranking`, `cv_analysis`
- affected features: `cv_system`, `inspection_debugging`, `settings_system`
- implementation code: out of scope for this document
- implementation plan: required after approval
- GitNexus: FTS index is degraded; current source, tests, config, and managed stage
  documents are authoritative

## Current-State Diagnosis

Current ranking has useful deterministic helpers but no single baseline truth:

- `config/policy/ranking.yaml` owns six top-level weights, but
  `src/fitcv/ranking.py` duplicates numeric defaults in code.
- current factors are `ai_score`, `must_have_match`, `vector_similarity`,
  `title_relevance`, `seniority_fit`, and ambiguous `preference_fit`.
- Phase 1 emits `location_fit` and `language_fit` with stable `ranking_enabled`
  and `ranking_value`, but ranking does not consume them.
- `vector_similarity` affects both final score and tie-break order despite being
  retrieval evidence.
- `compute_final_score` creates `final_score`, while downstream labels usually
  come from model-authored `fit_label`; score and label therefore have different
  owners.
- `ai_score.py` includes thresholds in the AI prompt and AI-score fingerprint,
  asks the model for a label, and derives a label again when one is absent.
- `agentic_cv_analysis.resolve_ranked_job_fit` consumes `fit_label`, then falls
  back directly to `ai_score`; it does not consume the composite score.
- `preference_fit` means declared domain, role-family, and work-mode alignment,
  but the name conflicts with future learned preference.
- missing-value defaults are applied per row, but normalizer identities and
  baseline policy fingerprints are not persisted.
- ranking artifacts expose weights and samples but do not persist one immutable
  ranking-v2 contract payload or effective structured weights.
- mutable `job_url` remains an ordering key even though the pipeline already
  owns stable `raw_job_fingerprint` identity.

## Key Deliverables

### Deliverable 1: one ranking-v2 policy owner

`config/policy/ranking.yaml` owns all mutable baseline numbers. Code owns factor
IDs, algorithms, validation, and fingerprint construction. No numeric fallback
is duplicated in `ranking.py`, `ranking_contract.py`, `ai_score.py`, settings
schema, or pipeline code.

### Deliverable 2: one stable baseline algebra

One `ranking_contract.py` path validates factors, derives policy-level effective
weights, computes contributions, computes `structured_fit`, computes
`baseline_fit`, maps `baseline_fit_label`, and builds fingerprints. Full-run and
resume execution call the same path.

### Deliverable 3: one label SSOT

Ranking owns `baseline_fit_label`. CV analysis and generation consume that
persisted label. Model-authored labels and personalized scores cannot gate CV
generation.

### Deliverable 4: one explicit label-migration proof

Ranking artifact diagnostics compare available legacy model labels with the new
threshold-derived baseline labels. The report owns comparable-row count, 3x3
migration matrix, total migration rate, direct `strong`/`skip` crossings, and
`passed | failed | insufficient_evidence` status.

### Deliverable 5: one truthful artifact and downstream contract

Ranking stage artifact v8, checkpoint compatibility adapters, settings schema,
cross-cutting docs, stage sources, and feature source describe the same baseline
fields and owners.

## Canonical Ownership

| Truth | Canonical owner | Derived consumers |
|---|---|---|
| AI semantic score and reasoning | `src/fitcv/ai_score.py` | ranking boundary |
| location/language facts and policy projection | Phase 1 factor contract | ranking boundary |
| factor IDs and normalizer algorithms | existing helpers named below, composed by `src/fitcv/ranking_contract.py` | ranking runtime |
| baseline numeric policy | `config/policy/ranking.yaml` | config loader, settings, ranking |
| baseline score, label, order, fingerprints | ranking stage | artifacts, CV analysis, exports |
| CV generation gate | persisted `baseline_fit_label` | `agentic_cv_analysis.py` |
| shortlist similarity and rank | shortlist stage | diagnostics only after shortlist |

Settings UI is an adapter over these policy owners. It may expose validated
fields but may not copy defaults, factor lists, or threshold semantics.

Control-plane and worker replay signatures consume the canonical
`ranking_contract_fingerprint`. They do not rebuild ranking envelopes from
selected config subtrees in separate modules.

## Ranking Policy Contract

`config/policy/ranking.yaml` is replaced by one exact object:

```yaml
ranking_policy:
  policy_version: ranking-v2
  normalizer_version: absolute-fit-v1
  active_baseline_mode: holistic_ai_only
  baseline_weights:
    holistic_ai_fit: 1.0
    structured_fit: 0.0
  structured_factor_weights:
    must_have_match: 0.30
    title_relevance: 0.20
    seniority_fit: 0.15
    declared_preference_fit: 0.15
    location_fit: 0.10
    language_fit: 0.10
  declared_preference_component_weights:
    domain: 0.50
    role_family: 0.30
    work_mode: 0.20
  missing_value_defaults:
    holistic_ai_fit: 0.0
    must_have_match: 0.5
    title_relevance: 0.5
    seniority_fit: 0.5
    declared_preference_fit: 0.5
    location_fit: 0.5
    language_fit: 0.5
  fit_label_thresholds:
    strong: 0.70
    stretch: 0.40
  label_migration_gate:
    maximum_total_label_migration_rate: 0.10
    maximum_strong_skip_crossings: 0
```

Phase 3 validates `active_baseline_mode: holistic_ai_only` together with exact
baseline weights `holistic_ai_fit: 1.0` and `structured_fit: 0.0`. Structured
factors remain diagnostics and future inputs. Another mode or weight mix requires
a later reviewed policy version.

Validation is exact:

- reject unknown or missing top-level policy keys
- reject unknown or missing factor IDs
- reject any active mode other than `holistic_ai_only` in Phase 3
- require baseline weights to equal exact Phase 3 mode weights `1.0/0.0`
- require structured factor weight sets to sum to `1.0`
- require finite values in `[0.0, 1.0]`
- require `strong > stretch`
- require migration rate in `[0,1]` and nonnegative crossing limit
- reject retired `ranking_weights`, `preference_fit_weights`,
  `missing_value_defaults`, `ranking_null_defaults`, and old settings keys
- reject config when eligibility factor IDs or ranking factor IDs drift

No code fallback supplies these values. Test fixtures use a minimal complete
policy fixture rather than invoking hidden defaults.

`config/policy/cv.yaml` keeps separate evidence-gap and generation-review
thresholds. Those values do not classify baseline ranking fit and are unchanged
by Phase 3.

## Factor Normalization Contract

Every normalized factor is absolute and globally stable under the same contract:

| Factor | Absolute normalizer | Missing behavior |
|---|---|---|
| `holistic_ai_fit` | clamp finite raw `ai_score` to `[0,1]` once at AI boundary | `0.0` after typed AI failure |
| `must_have_match` | existing `ranking.compute_must_have_match` | `0.5` when no required-skill evidence |
| `title_relevance` | existing `ranking.compute_title_relevance` | `0.5` when role evidence is absent |
| `seniority_fit` | existing `ranking.compute_seniority_fit` | `0.5` when either side is unknown |
| `declared_preference_fit` | renamed existing `ranking.compute_preference_fit_details` | `0.5` when no declared preference is available |
| `location_fit` | Phase 1 persisted `ranking_value` | neutral `0.5` only for legacy checkpoint absence |
| `language_fit` | Phase 1 persisted `ranking_value` | neutral `0.5` only for legacy checkpoint absence |

No factor uses cohort rank, percentile, z-score, min-max scaling, Top-N position,
or values from other jobs. Same normalized input plus same policy and normalizer
versions always yields same output globally.

`preference_fit` is renamed everywhere to `declared_preference_fit`.
`location_type` inside its component payload is renamed `work_mode`; actual
geography remains `location_fit`.

## Effective Structured Weights

Eligibility mode changes factor participation, not per-job weighting:

```text
ranking_only -> factor participates with configured structured weight
hard_gate    -> factor does not participate after eligibility gate
disabled     -> factor does not participate
```

At config load, derive one `effective_structured_factor_weights` object from the
validated ranking policy and validated eligibility policy:

1. retain always-on core factors
2. retain `location_fit` or `language_fit` only when its eligibility mode is
   `ranking_only`
3. remove weights for non-ranking factors
4. renormalize retained weights once to sum to `1.0`
5. fingerprint configured weights, retained IDs, effective weights, and
   eligibility policy fingerprint

The derived object is constant for every job in one run/policy context. Missing
job evidence uses the factor's fixed missing value. Weights are never
renormalized per job.

Example: if language is a hard gate and location remains ranking-only, language
weight is removed once and the other five weights are scaled by the same fixed
factor. Two jobs with identical factor values therefore remain comparable.

## Baseline Algebra

For structured factors `K`:

```text
structured_fit = sum(effective_structured_weight[k] * normalized_factor[k])

baseline_fit =
  baseline_weight[holistic_ai_fit] * holistic_ai_fit
  + baseline_weight[structured_fit] * structured_fit

baseline_fit_label =
  strong   when baseline_fit >= strong_threshold
  stretch  when baseline_fit >= stretch_threshold
  skip     otherwise
```

All inputs and outputs are finite and in `[0,1]`. Floating-point comparison uses
the unrounded value. Display rounding never feeds ordering, labels, fingerprints,
or later optimization.

Production ordering is one total order:

```text
baseline_fit DESC, raw_job_fingerprint ASC, job_url ASC
```

No hidden tie-break uses AI score, structured score, vector similarity, input
order, database order, or model label.

`raw_job_fingerprint` is required at ranking boundary and reuses the existing
stable identity produced by enrichment. `job_url` remains the final secondary
tie-break and display/provenance field. Missing stable identity is invalid input.

## Canonical Ranking Row

New ranking rows persist these canonical fields:

```text
job_url
raw_job_fingerprint
holistic_ai_fit
structured_fit
baseline_fit
baseline_fit_label
baseline_rank
baseline_mode
normalized_factors:
  <factor_id>:
    value
    source
    normalizer_id
    missing_default_applied
    ranking_enabled
    configured_weight
    effective_weight
    contribution
declared_preference_components
ranking_policy_version
normalizer_version
ranking_contract_fingerprint
eligibility_policy_fingerprint
```

`ranking_contract_fingerprint` is the SHA-256 of canonical JSON containing the
exact ranking policy payload, effective structured weights, ordered factor and
normalizer IDs, eligibility policy fingerprint, stable-identity order version,
and legacy-adapter version. No consumer builds a partial or competing hash.

Shortlist evidence remains present only as non-contributing provenance:

```text
vector_similarity
vector_rank
shortlist_origin
```

Internal pipeline, checkpoint, artifact, CV-analysis, and persistence code use
`baseline_fit`, `baseline_fit_label`, and `baseline_rank` only. `final_score`,
`fit_label`, `final_rank`, and `preference_fit` are retired internal names.

`ranking_contract.adapt_legacy_ranking_row` is the only legacy read adapter.
It canonicalizes old and new values before conflict comparison. Numeric strings
and equivalent floats compare after finite numeric coercion; labels compare after
trim/lower normalization.

`ranking_contract.project_legacy_ranking_aliases` is the only read-only external
CSV/API projection:

```text
final_score = baseline_fit
fit_label = baseline_fit_label
final_rank = baseline_rank
```

Aliases are never accepted as write input, persisted as competing truth, or
included separately in fingerprints. Alias equality has an explicit test.

## AI Score Boundary

AI scoring owns one holistic scalar and explanatory evidence, not a qualification
label.

Phase 3 advances the AI prompt/schema contract and requires model output:

```json
{
  "ai_score": 0.0,
  "score_reasoning": "...",
  "matched_strengths": [],
  "key_risks": []
}
```

Rules:

- parse and clamp `ai_score` once to `[0,1]`
- rename it to `holistic_ai_fit` only at ranking boundary
- remove fit-label thresholds from AI prompt and AI-score fingerprint
- stop asking the model for `fit_label`
- ignore a legacy response `fit_label` field if present
- advance prompt/schema fingerprint so old cached rows are not reused as v2
- keep AI reasoning and risks diagnostic; do not re-enter them as factors

This prevents AI from contributing once as score and again through model label or
copied subdimensions.

## Downstream Label Contract

`baseline_fit_label` is authoritative after ranking.

`agentic_cv_analysis.resolve_ranked_job_fit` must:

1. accept valid persisted `baseline_fit_label`
2. otherwise derive from finite persisted `baseline_fit` using the bound ranking
   policy thresholds
3. otherwise return `skip` with a missing-baseline diagnostic

It must not consult `ai_score`, model-authored labels, personalized score,
vector similarity, or CV-analysis gap findings to rewrite baseline fit.

`strong | stretch | skip` meanings and current thresholds remain unchanged while
`active_baseline_mode` is `holistic_ai_only`. Future latent residual changes
ordering only; it never changes this label or CV-generation gate.

Reporter text, artifact fields, UI labels, and diagnostics replace "reranker fit"
with "baseline fit" where they describe authoritative qualification.

## Checkpoint And Artifact Contract

Checkpoint schema remains v1. New writes use canonical ranking-v2 fields.

Checkpoint read compatibility is boundary-only:

- old `final_score` maps to `baseline_fit`
- old `fit_label` maps to `baseline_fit_label`
- old `final_rank` maps to `baseline_rank`
- missing Phase 1 factor results map to neutral values with
  `legacy_checkpoint_default_applied: true`
- conflicting old and canonical values are invalid input

No new checkpoint table or migration job is added.

Stage-transition artifact schema advances from
`stage_transition_artifacts_v7` to `stage_transition_artifacts_v8` because the
ranking block changes semantic shape. Run and stage envelope versions remain
unchanged.

`stages.ranking` records:

- exact ranking policy payload and canonical fingerprint
- active baseline mode and baseline weights
- configured and effective structured weights
- factor normalizer IDs and missing-default counts
- factor coverage and contribution summaries
- baseline label distribution
- input, ranked, and scored-not-ranked samples using canonical fields
- AI-score reuse counts under the new prompt fingerprint
- legacy checkpoint adaptation count

CV-analysis artifact records the consumed `baseline_fit_label` and
`ranking_contract_fingerprint`. It does not restate ranking policy numbers.

Settings schema removes retired ranking keys. Existing generic settings-store
invalid-key cleanup removes stale saved rows after schema cutover; no semantic
mapping is attempted because vector-inclusive old weights do not mean the same
thing as ranking-v2 policy. Phase 3 baseline weights remain config-only because
the active mode fixes them to `1.0/0.0`; operators may save only supported
structured-factor, declared-preference, missing-default, and threshold settings.

Control-plane run summaries, worker snapshots, replay contexts, and status-row
normalizers use canonical baseline names. Legacy `reranker_fit_label` and
`ranking_fit_label` inputs are accepted only by read adapters for historical run
artifacts and project to `baseline_fit_label` without dual persistence.

## Label Migration Gate

The shared ranking contract computes a migration summary from rows that contain
both a valid legacy model label and the new threshold-derived label. It does not
use star ratings, applications, synthetic labels, or a second evaluator formula.

The summary contains comparable-row count, fixed label-order 3x3 migration
matrix, total migration rate, direct `strong`/`skip` crossings, ordered reason
codes, and `passed | failed | insufficient_evidence` status.

Cutover passes only when total migration is within policy limit and direct
`strong`/`skip` crossings do not exceed policy limit. No comparable rows yields
`insufficient_evidence`; explicit operator acceptance is then required and must
be recorded in plan outcome. The user request to execute this plan is that
acceptance for this implementation run.

## Admissible-Case Matrix

| Case | Baseline behavior | Required evidence |
|---|---|---|
| all factors present | compute fixed contributions | full factor record |
| core structured factor missing | use fixed policy default | missing flag |
| location ranking-only | include Phase 1 `ranking_value` | factor/policy fingerprint |
| location hard-gated | exclude weight once after gate | effective-weight fingerprint |
| language disabled | exclude weight once | effective-weight fingerprint |
| both optional factors excluded | renormalize four core weights once | policy-level derived weights |
| AI scoring failure | `holistic_ai_fit=0.0` | typed AI failure |
| old checkpoint lacks Phase 1 factors | neutral compatibility values | legacy adaptation diagnostic |
| old and canonical fields conflict | reject input | deterministic error |
| exact score tie | `raw_job_fingerprint ASC, job_url ASC` | total-order test |
| missing stable fingerprint | reject row | deterministic identity error |
| legacy labels available | compute migration summary | fixed-order matrix and status |
| no comparable legacy labels | require explicit operator acceptance | `insufficient_evidence` status |
| future latent residual differs | ordering may change later; label does not | baseline label preserved |

## Task/Wave Breakdown

### Wave 1: freeze contracts and failing tests

**Purpose:**
- make current overlap, duplicate ownership, and downstream label drift visible
  before implementation

**Steps:**
- [x] inventory every ranking weight, threshold, fallback, factor, field alias,
  prompt label, settings key, checkpoint field, artifact field, and downstream
  label consumer
- [x] add failing strict-policy tests for exact keys, sums, ranges, thresholds,
  policy versions, normalizer versions, and retired keys
- [x] add failing algebra tests for baseline weights, effective weights, missing
  values, total ordering, and fingerprints
- [x] add failing downstream tests proving only baseline label gates CV analysis
- [x] add failing label-migration tests for pass, fail, insufficient evidence,
  and direct `strong`/`skip` crossings

**Verification:**
- [x] tests fail only because ranking-v2 contract is absent

**Exit Criteria:**
- every implementation change has one observable failing proof

### Wave 2: establish config and ranking-contract SSOT

**Purpose:**
- create one validated policy payload and one shared baseline algebra

**Steps:**
- [x] replace ranking config with exact `ranking_policy` object
- [x] remove code-owned numeric ranking defaults and retired config keys
- [x] centralize factor IDs, normalizer IDs, validation, effective-weight
  derivation, baseline computation, labels, and fingerprints in
  `ranking_contract.py`
- [x] rename declared-preference functions, config, diagnostics, and row fields
- [x] consume Phase 1 location/language projection without recomputation

**Verification:**
- [x] one source search finds no copied ranking numbers or retired factor names
- [x] same policy and factors produce byte-identical canonical payloads and hashes

**Exit Criteria:**
- config and ranking contract have one owner each and no alternate formula

### Wave 3: migrate runtime, checkpoints, artifacts, and downstream labels

**Purpose:**
- make full-run, resume, persistence, observability, and CV gates symmetric

**Steps:**
- [x] advance AI prompt/schema to score-only semantic output
- [x] replace ranking row construction and ordering with canonical baseline fields
- [x] add boundary-only old-checkpoint adaptation and reject conflicts
- [x] advance stage artifact to v8 and update samples/quality metrics
- [x] update CV analysis to consume baseline label or baseline-score fallback only
- [x] update settings schema from config-owned values and reject retired controls
- [x] replace app/worker copied policy-envelope signatures with the canonical
  ranking contract fingerprint
- [x] update control-plane and worker historical-row adapters to project legacy
  label names into canonical baseline fields
- [x] update external compatibility projection without persisting aliases

**Verification:**
- [x] full run and resume produce identical ranking rows and CV decisions
- [x] latent, vector, model-label, and display-only values cannot change baseline label

**Exit Criteria:**
- every downstream path consumes persisted baseline truth

### Wave 4: run ablation gate and reconcile lifecycle docs

**Purpose:**
- prove overlap policy and finish source-first documentation

**Steps:**
- [x] compute label-migration evidence from available legacy rows through the
  shared ranking contract
- [x] record `insufficient_evidence` plus explicit operator acceptance when no
  comparable legacy rows exist
- [x] update ranking and CV-analysis stage sources plus CV-system feature source
- [x] update architecture, configuration, and pipeline docs
- [x] regenerate planning and architecture metadata

**Verification:**
- [x] Phase 3 rejects combined active mode; passing report proves follow-up eligibility only
- [x] generated metadata and lifecycle validators are current

**Exit Criteria:**
- baseline authority, migration status, and downstream label owner are explicit

## Design Decisions

### Decision: AI-only is the only Phase 3 active mode

- context: structured factors are deterministic but not yet proven more robust
  than holistic AI
- choice: activate `holistic_ai_only`; expose structured factors only as
  diagnostics and future inputs
- alternatives considered:
  - activate combined baseline by construction
  - delete structured factors
- impact:
  - Phase 3 establishes stable contracts without speculative baseline modes

### Decision: one shared function owns score and label

- context: current composite score and model label have different owners
- choice: ranking contract computes both `baseline_fit` and
  `baseline_fit_label`
- alternatives considered:
  - keep model-authored label authoritative
  - let CV analysis reclassify jobs
- impact:
  - one persisted value controls every downstream fit gate

### Decision: model label is removed from AI semantics

- context: asking AI for score and label duplicates threshold logic and can
  contradict itself
- choice: AI v2 returns one scalar plus evidence; ranking thresholds own labels
- alternatives considered:
  - preserve AI label as fallback
- impact:
  - prompt fingerprint changes and prior AI-score reuse is invalidated safely

### Decision: structured symmetry does not imply equal weights

- context: factors share one envelope but answer different semantic questions
- choice: all factors use the same record/algebra while config owns explicit
  unequal weights
- alternatives considered:
  - equal weights
  - factor-specific ranking code
- impact:
  - uniform implementation without pretending equal importance

### Decision: hard-gated factors leave ranking weights once per policy

- context: a hard gate should not also change surviving jobs differently
- choice: remove non-ranking weights and renormalize once at policy load
- alternatives considered:
  - per-job renormalization
  - keep weight with neutral value
- impact:
  - scores remain globally comparable within one policy context

### Decision: no cohort-relative normalization

- context: Top-N and candidate population changes would alter identical job scores
- choice: every normalizer is absolute and versioned
- alternatives considered:
  - min-max, percentile, z-score, rank normalization
- impact:
  - same evidence always gives same baseline score under same policy

### Decision: stable fingerprint is the final identity tie-break

- context: AI, structured, and vector tie-breaks create hidden unweighted influence
- choice: order by raw baseline score, existing `raw_job_fingerprint`, then job URL
- alternatives considered:
  - preserve vector similarity tie-break
  - preserve input order
- impact:
  - deterministic total order survives URL drift, duplicates, and resumes

### Decision: compatibility aliases exist only at serialization boundary

- context: existing external consumers may still read old names
- choice: derive old names from canonical fields on output only
- alternatives considered:
  - persist both old and new names
  - break all consumers immediately
- impact:
  - compatibility without second internal truth

### Decision: label-owner cutover has explicit migration evidence

- context: current runtime accepts valid model-authored labels, while ranking-v2
  derives labels from score thresholds
- choice: compute one migration summary from available legacy rows; block direct
  strong/skip crossings and require explicit acceptance when evidence is absent
- alternatives considered:
  - claim label semantics are unchanged
  - keep model labels as competing truth
- impact:
  - cutover risk is visible without preserving duplicate label authority

## Invariants

1. `config/policy/ranking.yaml` is the only mutable baseline numeric owner.
2. Code contains no copied production ranking weights or thresholds.
3. AI contributes to baseline exactly once through `holistic_ai_fit`.
4. No AI reasoning subdimension is a structured factor.
5. Exactly six structured factor IDs exist in ranking-v2.
6. `declared_preference_fit` never means learned preference.
7. Actual geography and work mode remain distinct factors/components.
8. `vector_similarity` and `vector_rank` never affect baseline score, label, or
   tie-break order.
9. Every factor value, weight, contribution, `structured_fit`, and
    `baseline_fit` is finite and within `[0,1]`.
10. Configured and effective weight sets each sum to `1.0` within tolerance.
11. Effective structured weights are derived once per policy context, never per
    job.
12. Same values plus same fingerprints produce same score and label globally.
13. Display rounding does not affect semantic computation.
14. `baseline_fit_label` is the only internal owner of `strong | stretch | skip`
    after ranking.
15. CV analysis never derives fit from personalized score, vector score, or AI
    score when baseline fields exist.
16. Future learned preference may change ordering only.
17. Every ranked row has non-empty `raw_job_fingerprint` stable identity.
18. Label migration status is `passed`, `failed`, or `insufficient_evidence`.
19. Direct `strong`/`skip` crossings cannot pass the migration gate.
20. Checkpoint schema stays v1 and new writes use canonical fields only.
21. Compatibility aliases are derived and never persisted as competing truth.
22. Full-run and resume ranking behavior is contract-equivalent.
23. Stage artifact v8 binds the exact ranking and eligibility fingerprints.
24. Phase 3 creates no rating ledger, learned vector, decision-learning policy,
    benchmark evaluator, or optimizer runtime.

## Acceptance Criteria

- config loads only the exact ranking-v2 policy shape
- retired ranking keys fail with actionable errors
- location/language participation follows eligibility mode symmetrically
- fixed structured weights remain identical across all rows in a run
- AI-only active mode produces threshold-derived labels for finite scores and
  reports migration from available legacy model labels
- vector value changes cannot change baseline score, label, or order except when
  stable identity itself differs
- model-returned label changes cannot change baseline label
- full-run and resume produce identical canonical rows and fingerprints
- old schema-v1 checkpoints adapt deterministically; conflicting dual fields fail
- CV-analysis skip/continue decisions use baseline label only
- artifact schema v8 exposes factors, contributions, effective weights, and
  fingerprints without copied policy truth in CV-analysis stage
- label migration emits deterministic matrix, status, and reason ordering
- absent comparable legacy labels emits `insufficient_evidence` and records the
  explicit operator acceptance
- no new dependency, database table, service, ORM, or solver import is added

## Non-Goals

- collecting or displaying 1–5-star ratings
- creating decision episodes or rating events
- compiling ordinal ratings into pairwise constraints
- training or activating a latent preference vector
- adding decision-learning policy or choosing an optimizer/solver
- changing embedding model or shortlist membership
- changing Phase 1 location/language extraction or hard-gate semantics
- using application history that does not exist
- treating user interest stars as qualification labels
- auto-tuning weights from current rankings
- creating a generic multi-domain ranking framework
- building a qualification benchmark evaluator

## Risks And Mitigations

| Risk | Mitigation |
|---|---|
| AI score overlaps deterministic factors | structured factors remain diagnostics; no combined mode in Phase 3 |
| model score and old label disagree | derive one baseline label and report migration before cutover |
| label migration evidence is absent | record `insufficient_evidence` and explicit operator acceptance |
| hard-gate modes change score scale | derive and fingerprint effective weights once per policy |
| old checkpoint lacks Phase 1 factors | neutral boundary adapter plus explicit diagnostic |
| compatibility aliases become second SSOT | output-only projection; reject aliases on input |
| hidden vector influence survives in tie-break | fingerprint/URL identity tie-break and isolated-input tests |
| config and code defaults drift | no production numeric defaults in code |
| settings page preserves retired controls | schema derives new exact keys and rejects old paths |

## Validation Plan

- proof target: one numeric ranking owner exists
  - method: config validation tests and source search for copied numeric defaults
  - evidence: only `config/policy/ranking.yaml` contains production baseline values
- proof target: normalization is globally stable
  - method: repeat identical factor payload across different cohorts, orderings,
    Top-N sizes, and unrelated jobs
  - evidence: identical factor values and fingerprints produce identical scores
- proof target: factor participation is symmetric
  - method: exhaustive location/language mode matrix for
    `ranking_only | hard_gate | disabled`
  - evidence: effective weights are derived once, sum to one, and are identical
    across rows
- proof target: AI contribution appears once
  - method: isolated-input tests varying AI score, AI reasoning, old model label,
    and each structured factor separately
  - evidence: only `holistic_ai_fit` changes AI contribution; reasoning/label do not
- proof target: vector evidence is retrieval-only
  - method: vary vector similarity/rank while holding job URL and baseline factors
  - evidence: baseline score, label, and order key remain unchanged
- proof target: one label controls downstream gates
  - method: ranking and CV-analysis tests with conflicting AI/model/personalized
    values
  - evidence: persisted baseline label wins; missing label derives from baseline
    score only
- proof target: full-run and resume are symmetric
  - method: resume from shortlist and ranking checkpoints, including legacy v1
  - evidence: canonical ranking rows, fingerprints, labels, and CV decisions match
- proof target: artifacts are truthful and versioned
  - method: stage artifact golden and worker continuation tests
  - evidence: v8 ranking block survives continuation and CV-analysis references
    exact baseline fingerprint
- proof target: label-owner cutover is explicit
  - method: migration fixtures for passing, excessive migration, direct crossing,
    and insufficient evidence
  - evidence: deterministic report status/reasons and recorded acceptance

Focused verification target:

```text
python -m pytest tests/test_config.py tests/test_ranking.py tests/test_ai_score.py
python -m pytest tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py
python -m pytest tests/test_agentic_cv_analysis.py
python -m pytest tests/test_fitcv_cp/test_settings_schema.py
python scripts/generate_planning_lineage.py
python tools/docs/generate_architecture_metadata.py --check
python scripts/validate_planning_lifecycle.py
python scripts/validate_repo_contracts.py --fast
git diff --check
```

## Completion Criteria

Phase 3 implementation is complete when:

1. all Key Deliverables and Acceptance Criteria pass
2. ranking-v2 policy is the exact validated numeric SSOT
3. production uses explicit `holistic_ai_only` baseline authority
4. six structured factors and contributions are available under one uniform row
   contract
5. location/language weights follow Phase 1 eligibility modes once per policy
6. vector evidence has no ranking influence
7. baseline score, label, rank, normalizer, and fingerprints persist canonically
8. CV analysis and later stages consume baseline label only
9. full-run, resume, checkpoint, artifact, settings, and export boundaries agree
10. label migration is passing or explicitly `insufficient_evidence` with
    operator acceptance recorded
11. no rating, benchmark evaluator, decision-learning, optimization, activation,
    database, or solver scope leaks into Phase 3
12. docs and generated metadata are current
13. implementation plan is completed with fresh verification evidence

Canonical source-of-truth:

<LINK>
- `docs/superpowers/specs/2026-07-14-22-25-fitcv-inverse-optimization-master-ssot-symmetry-spec.md`
- `docs/superpowers/specs/2026-07-15-16-40-fitcv-inverse-optimization-phase-1-location-language-eligibility-spec.md`
- `docs/superpowers/specs/2026-07-15-19-01-fitcv-inverse-optimization-phase-2-vector-only-shortlist-spec.md`
- `docs/operating_system/governance/repo-governance.md`
- `docs/operating_system/lifecycle/doc-system-lifecycle.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
