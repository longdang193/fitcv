---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: fitcv-inverse-optimization-phase-5-symmetric-preference-compiler
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-stage-authority-contract
parent_spec: docs/superpowers/specs/2026-07-14-22-25-fitcv-inverse-optimization-master-ssot-symmetry-spec.md
targets:
  - config/policy/decision_learning.yaml
  - src/fitcv/config.py
  - src/fitcv/decision_feedback.py
  - docs/architecture.md
  - docs/configuration.md
  - docs/pipeline.md
  - docs/stages/ranking.source.yaml
  - docs/features/cv_system/feature.source.yaml
  - tests/test_config.py
  - tests/test_decision_feedback.py
related_features:
  - cv_system
related_stages:
  - ranking
---

# Detailed Spec: FitCV inverse optimization Phase 5 symmetric preference compiler

## Goal

Translate Phase 4 ordinal application-interest evidence into one deterministic,
versioned comparison algebra without asking pairwise questions, persisting a
second truth, or changing ranking.

Uniform flow:

```text
one immutable decision episode
+ complete append-only rating events through event_watermark
-> one provenance-preserving effective-rating reduction
-> every unordered alternative pair exactly once
-> omit unrated, equal, and below-gap pairs
-> orient every qualifying pair from higher rating to lower rating
-> apply versioned gap evidence weight
-> apply one episode-wide evidence budget scale
-> canonical ordered preference-edge set + diagnostics + fingerprints
```

Phase 5 consumes stars only as ordinal labels. It does not average ratings,
interpret equal ratings as exact utility equality, infer application history,
train a latent vector, invoke CVXPY, activate policy, or alter
`baseline_fit`, `strong | stretch | skip`, shortlist order, CV eligibility, or
current run results.

## Triage

- layer: `change`
- feature type: `MODIFY`
- parent: inverse-optimization master SSOT and symmetry specification
- dependencies: Phase 1 through Phase 4 implementations are complete
- affected stage: `ranking` as immutable evidence producer only
- affected features: `cv_system`, `inspection_debugging`
- primary lens: pure domain compiler and replay diagnostics
- generated refresh required: yes
- implementation code: out of scope for this document
- implementation plan: required after approval
- GitNexus: keyword index remains degraded; current source, tests, config, and managed docs are authoritative

## Current-State Diagnosis

Reusable owners:

- `config/policy/decision_learning.yaml` owns `decision-learning-v1`, domain
  `ranking_v1`, scale `application-interest-v1`, exact labels `1` through `5`,
  and `unrated`
- `DecisionEpisode` freezes compatible preference, qualification, ranking,
  baseline, embedding, rating-scale, candidate-set, and source fingerprints
- `DecisionAlternative` freezes one episode alternative, baseline evidence,
  normalized embedding, vector fingerprint, and displayed rank
- `DecisionRatingEvent` preserves immutable set/clear evidence with SQLite-owned
  `event_sequence`
- `reduce_rating_events(...)` derives current ordinal state from latest sequence
- SQLite remains append-only truth; no mutable current-rating table exists
- `build_contract_fingerprint(...)` is existing canonical hash helper
- Phase 4 UI and POST route already adapt native form values to domain records

Missing Phase 5 boundary:

- no compiler policy or compiler-policy fingerprint
- no effective-rating provenance record exposing latest source event
- no preference-edge record
- no deterministic pair enumeration
- no minimum clear-gap rule
- no gap evidence weights
- no episode evidence cap
- no compiler input or edge-set fingerprint
- no typed zero-edge result or omission diagnostics

## Key Deliverables

### Deliverable 1: one narrow compiler-policy extension

Extend `decision_learning_policy` with one exact `preference_compiler` block.
Keep rating labels and compiler semantics in the same policy file because they
form one versioned interpretation contract.

Canonical Phase 5 policy:

```yaml
preference_compiler:
  compiler_version: preference-compiler-v1
  minimum_rating_gap: 2
  gap_evidence_weights:
    "1": 1.0
    "2": 2.0
    "3": 3.0
    "4": 4.0
  max_episode_evidence_budget: 12.0
```

Rules:

- `compiler_version` is nonempty and exact for implementation v1
- `minimum_rating_gap` is integer `1..4`; shipped v1 value is `2`
- `gap_evidence_weights` contains exactly keys `1..4`
- all weights are finite, positive, and strictly increasing by gap
- `max_episode_evidence_budget` is finite and positive
- compiler policy is not exposed through settings UI or `.env.yaml`
- `compiler_policy_fingerprint` is `build_contract_fingerprint(...)` over the normalized
  `preference_compiler` block only
- `decision_learning_policy_fingerprint` is the existing full validated policy
  fingerprint and participates in compiler input and result identity
- changing any compiler value changes compiler-policy fingerprint
- changing rating-scale labels or any other decision-learning policy value changes
  the full policy fingerprint even when compiler values stay unchanged
- changing rating-label semantics requires a new `rating_scale.version`
- changing algorithm semantics requires a new `compiler_version`

### Deliverable 2: one provenance-preserving reducer path

Add one immutable effective-state record:

```text
EffectiveRatingState
  episode_id
  alternative_id
  rating: unrated | 1 | 2 | 3 | 4 | 5
  source_event_id: string | null
  event_sequence: integer | null
```

Reduction rules:

- latest SQLite `event_sequence` at or below watermark wins
- latest `set_rating` yields exact ordinal rating and its event ID
- latest `clear_rating` yields `unrated` and preserves clear-event provenance
- no event yields ephemeral `unrated` with null provenance
- timestamps and UUID ordering never determine current state

Implement one canonical state reducer. Keep existing
`reduce_rating_events(...)` as a compatibility projection from canonical states
to `unrated | 1..5`. UI and compiler therefore share one reduction algorithm;
there is no second current-state owner.

### Deliverable 3: immutable compiler records

Add frozen records in `src/fitcv/decision_feedback.py`.

`PreferenceEdge`:

```text
preferred_alternative_id
other_alternative_id
rating_gap
evidence_weight
episode_bounded_weight
source_event_ids
compiler_version
```

`source_event_ids` is an ordered pair:

```text
(preferred endpoint effective set-event ID,
 other endpoint effective set-event ID)
```

`PreferenceCompilerDiagnostics`:

```text
alternative_count
rated_alternative_count
unordered_pair_count
omitted_unrated_pair_count
omitted_equal_pair_count
omitted_below_gap_pair_count
emitted_edge_count
raw_evidence_weight_sum
episode_scale
bounded_evidence_weight_sum
```

`PreferenceCompilerResult`:

```text
schema_version: preference_compiler_result_v1
status: compiled | insufficient_evidence
episode_id
event_watermark
compiler_version
compiler_policy_fingerprint
decision_learning_policy_fingerprint
compiler_input_fingerprint
edge_set_fingerprint
edges
diagnostics
```

Malformed or incompatible inputs raise `ValueError` at compiler boundary. They
do not return `insufficient_evidence` because malformed evidence is not an
admissible empty case.

### Deliverable 4: one symmetric pair compiler

Canonical callable shape:

```python
compile_preference_edges(
    episode,
    alternatives,
    events,
    *,
    event_watermark,
    decision_learning_policy,
) -> PreferenceCompilerResult
```

Boundary rules:

- inputs are plain Phase 4 immutable domain records
- function performs no DB query, config-file read, HTTP work, or global mutation
- `event_watermark` is a nonnegative integer
- alternatives belong to exactly one episode
- alternative IDs and displayed ranks are unique
- selected events belong to same episode and known alternatives
- selected event scale matches episode and policy scale
- policy domain matches episode domain
- episode ranking, baseline, embedding, preference, qualification, candidate,
  and source fingerprints remain frozen; no cross-episode merge occurs
- events above watermark are ignored for replay
- persisted events at or below watermark require positive sequence values
- duplicate selected event IDs or event sequences are invalid

Pair accounting and enumeration:

1. sort alternatives by `alternative_id`
2. resolve effective ratings through canonical state reducer
3. compute total unordered-pair count as `n * (n - 1) // 2`
4. compute unrated omission count as total pairs minus rated pairs
5. enumerate each unordered pair of rated alternatives exactly once
6. omit pair if ratings are equal
7. compute `rating_gap = abs(rating_a - rating_b)`
8. omit pair if gap is below policy minimum
9. orient edge from higher rating to lower rating
10. map gap to policy evidence weight
11. order final edges by
    `(preferred_alternative_id, other_alternative_id)`

Use standard-library pair enumeration. Do not add a graph abstraction,
transitive reduction, matrix wrapper, or dependency.

### Deliverable 5: one episode budget and fingerprint contract

For emitted edges:

```text
raw_evidence_weight_sum = sum(evidence_weight)

episode_scale = min(
  1.0,
  max_episode_evidence_budget / raw_evidence_weight_sum
)

episode_bounded_weight = evidence_weight * episode_scale
```

When no edges exist:

```text
raw_evidence_weight_sum = 0.0
episode_scale = 1.0
bounded_evidence_weight_sum = 0.0
status = insufficient_evidence
```

One common `episode_scale` applies to every edge in an episode. Therefore:

- episode cap limits large episodes
- relative gap-weight order is preserved
- one-edge episodes retain full configured evidence weight
- total episode weight is capped, not normalized to one

Canonical compiler input fingerprint payload:

```text
schema_version: preference_compiler_input_v1
episode_id
candidate_set_fingerprint
rating_scale_version
event_watermark
compiler_version
compiler_policy_fingerprint
decision_learning_policy_fingerprint
effective_states sorted by alternative_id
```

Each effective-state fingerprint row contains:

```text
alternative_id
rating
source_event_id
event_sequence
```

Canonical edge-set fingerprint payload:

```text
schema_version: preference_edge_set_v1
episode_id
event_watermark
compiler_version
compiler_policy_fingerprint
decision_learning_policy_fingerprint
compiler_input_fingerprint
edges in canonical order
```

Diagnostics are derived proof and do not participate in edge-set identity.
Recomputing diagnostics from the same canonical effective states, policy, and
edges must match exactly.

### Deliverable 6: no new runtime or persistence surface

Phase 5 remains a pure compiler handoff for Phase 6.

Do not add:

- SQLite preference-edge table
- current-edge cache
- API route
- admin control
- settings control
- background job
- pipeline stage
- result-ledger schema change
- CVXPY or NumPy import
- solver record
- learned vector
- activation state
- ranking effect

Phase 6 may consume compiler results directly and decide its own training-run
persistence contract. Phase 5 does not scaffold that future layer.

## Detailed Compiler Contract

### Compatibility gate

Compiler accepts one episode only when all are true:

- policy domain equals episode domain
- policy rating-scale version equals episode rating-scale version
- compiler policy validates exactly
- every alternative references episode ID
- every selected event references episode ID
- every selected event alternative exists in alternatives
- every selected event rating-scale version equals episode scale
- alternative set is nonempty
- compiler recomputes the Phase 4 canonical candidate-set payload from sorted
  alternatives and requires its fingerprint to equal
  `episode.candidate_set_fingerprint`
- candidate-set identity remains episode-owned; no count-only or URL-based check is accepted

Compiler never compares alternatives across:

- episode IDs
- preference contexts
- qualification contexts
- ranking contracts
- baseline policy fingerprints
- embedding contracts or dimensions
- rating-scale versions
- compiler-policy fingerprints

### Watermark replay

`event_watermark` defines one immutable evidence snapshot.

- `0` is admissible and selects no events
- positive watermark selects events with sequence `<= watermark`
- later events remain stored but do not affect replay
- repeated compilation from same inputs and watermark is structurally equal and
  has identical fingerprints
- moving watermark forward may add, change, or remove current edges through set
  and clear events
- moving watermark backward never reads future state

Caller owns complete event loading through watermark. Phase 5 does not query
SQLite or claim completeness from sequence continuity because SQLite sequence is
global and may contain gaps from other episodes.

### Exhaustive pair semantics

For effective states in `{unrated,1,2,3,4,5}`:

| Left | Right | Result |
| --- | --- | --- |
| unrated | any | omit as unrated |
| any | unrated | omit as unrated |
| same rated value | same rated value | omit as equal ordinal band |
| rated values with gap `< minimum_rating_gap` | rated value | omit as below-gap |
| rated values with gap `>= minimum_rating_gap` | rated value | one directed edge |

For qualifying pairs, swapping endpoint input order:

- swaps comparison orientation only when rating ownership swaps
- preserves gap
- preserves evidence weight
- preserves episode-bounded weight
- preserves canonical final result after alternative sorting

Equal ratings produce no equality constraint. They mean same observed ordinal
band only.

### No transitive reduction

Given ratings `5`, `3`, and `1` with minimum gap `2`, compiler emits all three
qualifying edges:

```text
5 > 3
5 > 1
3 > 1
```

Do not delete `5 > 1`. Phase 6 uses per-edge slack, margins, and weights;
transitive deletion changes optimization evidence.

### Diagnostics

Every unordered pair contributes to exactly one diagnostic bucket:

```text
omitted_unrated
omitted_equal
omitted_below_gap
emitted
```

Invariant:

```text
unordered_pair_count
= omitted_unrated_pair_count
+ omitted_equal_pair_count
+ omitted_below_gap_pair_count
+ emitted_edge_count
```

Diagnostics use integer counts and finite weights. They are inspection output,
not a second decision source.

## Admissible-Case Matrix

| Case | Compiler result | Status |
| --- | --- | --- |
| no rating events | no edges | insufficient_evidence |
| one rated alternative | no edges | insufficient_evidence |
| latest event is clear | endpoint unrated; related pairs omitted | insufficient_evidence or compiled from other pairs |
| two equal ratings | no edge | insufficient_evidence |
| ratings differ by one under v1 | no edge | insufficient_evidence |
| ratings differ by two | one directed edge with weight `2.0` | compiled |
| ratings differ by three | one directed edge with weight `3.0` | compiled |
| ratings differ by four | one directed edge with weight `4.0` | compiled |
| many qualifying pairs under budget | full configured weights | compiled |
| many qualifying pairs over budget | one common scale caps total | compiled |
| rating changed before watermark | latest selected set event wins | deterministic |
| rating changed after watermark | later event ignored | deterministic replay |
| rating cleared before watermark | endpoint becomes unrated | deterministic |
| input alternative order shuffled | same output and fingerprints | deterministic |
| input event order shuffled | same output and fingerprints | deterministic |
| contradictory preferences across episodes | separate episode edge sets retained | valid for Phase 6 |
| mixed episode or scale | boundary rejection | invalid input |
| unknown alternative event | boundary rejection | invalid input |
| duplicate selected event sequence or ID | boundary rejection | invalid input |
| invalid policy weight or budget | policy rejection | invalid input |

## Task/Wave Breakdown

### Wave 1: freeze policy, provenance, and failing tests

**Purpose:** define exact Phase 5 contract before compiler code.

**Steps:**

- [ ] add failing policy tests for exact compiler block and no shadow setting
- [ ] add failing reducer-provenance tests for set, change, clear, no-event, and watermark cases
- [ ] add exhaustive 36-case pair table
- [ ] add symmetry, permutation, repeatability, fingerprint, and diagnostic tests
- [ ] add malformed compatibility and policy tests

**Verification:**

- [ ] Phase 4 tests remain green before production edits
- [ ] new tests fail only because compiler behavior is absent

**Exit Criteria:** contract is executable through tests without solver assumptions.

### Wave 2: extend decision-learning policy and canonical reducer

**Purpose:** add compiler semantics without creating second rating truth.

**Steps:**

- [ ] extend policy YAML with exact v1 compiler block
- [ ] extend strict policy validation and fingerprinting
- [ ] reject runtime/env/settings shadows
- [ ] add `EffectiveRatingState`
- [ ] route existing rating-value reducer through canonical provenance reducer
- [ ] preserve Phase 4 UI-visible reducer behavior

**Verification:**

- [ ] config and reducer tests pass
- [ ] rating labels remain owned only by policy YAML
- [ ] one reducer algorithm determines both UI values and compiler provenance

**Exit Criteria:** policy and effective-state SSOT are ready for pair compilation.

### Wave 3: add pure symmetric compiler

**Purpose:** compile every admissible episode through one deterministic path.

**Steps:**

- [ ] add frozen edge, diagnostic, and result records
- [ ] validate episode, alternatives, events, watermark, and policy
- [ ] enumerate standard-library unordered pairs once
- [ ] orient qualifying pairs and attach exact source event IDs
- [ ] apply gap weights and episode scale
- [ ] compute input and edge-set fingerprints
- [ ] return typed `insufficient_evidence` for empty edge sets

**Verification:**

- [ ] all 36 rating pairs match table
- [ ] swaps preserve symmetry
- [ ] input permutations preserve output
- [ ] repeated compile is byte-equivalent
- [ ] budget cap and one-edge weight ordering hold
- [ ] all diagnostic buckets reconcile

**Exit Criteria:** compiler output is Phase 6-ready without persistence or solver code.

### Wave 4: reconcile docs and generated metadata

**Purpose:** expose compiler boundary without claiming learning or ranking use.

**Steps:**

- [ ] update configuration docs with compiler policy ownership
- [ ] update architecture and pipeline docs with pure compiler handoff
- [ ] update ranking stage source as evidence producer only
- [ ] add compiler capability evidence to CV and inspection feature sources
- [ ] regenerate feature, stage, lineage, history, architecture, and planning outputs
- [ ] run lifecycle and repo-contract checks

**Verification:**

- [ ] generated docs derive from source metadata
- [ ] source search finds no solver, persistence, activation, or ranking effect

**Exit Criteria:** spec is implementation-plan ready and docs remain source-derived.

## Design Decisions

### Decision: compiler stays in existing decision-feedback module

- context: Phase 5 is a small pure transformation over Phase 4 records
- choice: extend `src/fitcv/decision_feedback.py`
- alternatives considered:
  - create `preference_compiler.py`
  - add a service class
- impact:
  - one domain owner remains easy to replay and test
  - split module only when Phase 6 solver scope requires separate ownership

### Decision: one policy file owns rating interpretation and compilation

- context: compiler meaning depends directly on ordinal scale semantics
- choice: extend `decision_learning.yaml` with one narrow compiler block
- alternatives considered:
  - new compiler policy file
  - runtime settings
- impact:
  - no cross-file semantic drift
  - exact policy fingerprint captures all comparison semantics

### Decision: clear difference starts at two stars

- context: adjacent star bands are intentionally low-friction and may be noisy
- choice: v1 minimum gap is `2`
- alternatives considered:
  - compile every non-equal pair
  - require gap `3`
- impact:
  - adjacent ratings remain evidence but create no ordering edge
  - later change requires policy fingerprint change, not code branch

### Decision: gap weight equals ordinal gap in v1

- context: larger clear differences should count more without pretending ratings are cardinal utility
- choice: map gaps `1..4` to weights `1.0..4.0`
- alternatives considered:
  - constant edge weight
  - nonlinear learned weights
- impact:
  - monotonic evidence strength is explicit and versioned
  - optimizer still receives comparisons, not star averages

### Decision: episode budget caps rather than normalizes

- context: large episodes generate quadratic pair counts
- choice: cap total weight at `12.0` with one common scale
- alternatives considered:
  - normalize every episode to one
  - cap edge count
  - random sample pairs
- impact:
  - small episodes retain absolute gap evidence
  - large episodes cannot dominate only because more alternatives were rated
  - all qualifying pairs remain replayable

### Decision: compiler is pure and nonpersistent

- context: Phase 6 owns training-run and optimizer persistence
- choice: return immutable records and fingerprints only
- alternatives considered:
  - preference-edge SQLite table
  - cached current edge set
- impact:
  - append-only rating ledger stays sole evidence truth
  - edges rebuild deterministically from watermark
  - no migration or stale cache exists

### Decision: canonical reducer gains provenance, public value projection stays stable

- context: edges require exact source event IDs while UI requires simple values
- choice: one state reducer plus existing value projection
- alternatives considered:
  - second compiler-only reduction
  - mutable current-rating row
- impact:
  - one ordering algorithm owns current state
  - Phase 4 UI behavior remains unchanged

### Decision: no transitive reduction

- context: Phase 6 uses weighted slack and margins
- choice: retain every qualifying unordered pair
- alternatives considered:
  - graph transitive reduction
  - adjacent-rating-only edges
- impact:
  - evidence meaning stays faithful and deterministic
  - bounded episode size keeps quadratic enumeration acceptable

## Invariants

1. Append-only rating events remain sole persisted rating truth.
2. Existing `application_tracker` remains separate and uninferred.
3. One canonical reducer algorithm owns latest-event selection.
4. SQLite `event_sequence`, not timestamp or UUID, owns temporal order.
5. Watermark replay excludes later events deterministically.
6. Every selected event belongs to one episode and known alternative.
7. Every selected event scale matches episode and policy scale.
8. Compiler never crosses episode boundary.
9. Compiler never crosses preference, qualification, ranking, baseline,
   embedding, rating-scale, or compiler-policy boundary.
10. Recomputed alternative-set fingerprint equals episode candidate-set fingerprint.
11. Every potential unordered pair is accounted for exactly once.
12. Every rated unordered pair is visited exactly once and lands in exactly one
    rated-pair diagnostic bucket.
13. Unrated endpoint produces no edge.
14. Equal ratings produce no edge or equality constraint.
15. Gap below policy minimum produces no edge.
16. Qualifying pair produces exactly one directed edge.
17. Edge direction is always higher rating to lower rating.
18. `rating_gap` is exact integer difference.
19. Evidence weight comes only from versioned policy mapping.
20. Larger gap has larger evidence weight under valid policy.
21. One common episode scale applies to all emitted edges.
22. Episode bounded-weight sum never exceeds configured budget except normal
    floating-point tolerance asserted by tests.
23. One-edge episode retains full configured gap weight.
24. Compiler performs no transitive reduction or random sampling.
25. Edge order is deterministic and input-order independent.
26. `source_event_ids` contains exactly two current set-event IDs aligned with
    edge endpoints.
27. Compiler input fingerprint includes watermark and effective provenance.
28. Edge-set fingerprint excludes diagnostics and includes canonical edges.
29. Same canonical input produces structurally equal result and identical fingerprints.
30. Zero edges are valid `insufficient_evidence`.
31. Malformed or incompatible inputs fail closed before edge emission.
32. Phase 5 changes no baseline score, fit label, shortlist, CV, or run result.
33. Phase 5 adds no DB table, route, worker, stage, settings control, or new dependency.
34. Phase 5 imports no NumPy, CVXPY, or solver package.
35. Rating labels remain ordinal and are never averaged.
36. Old v3 and v4 runs remain immutable and replayable.

## Acceptance Criteria

- policy loader accepts exact v1 compiler policy and rejects missing, extra,
  nonfinite, nonpositive, nonmonotonic, or malformed values
- no `.env.yaml`, settings schema, or admin settings page can shadow compiler policy
- Phase 4 rating-value reducer results remain unchanged
- canonical state reducer exposes latest source event ID and sequence
- event watermark `0` yields all alternatives unrated
- set, repeated set, change, and clear replay correctly at multiple watermarks
- exhaustive 36-case pair matrix passes
- minimum gap `2` suppresses adjacent ratings
- gaps `2`, `3`, and `4` produce weights `2.0`, `3.0`, and `4.0`
- input endpoint swap preserves symmetric result
- alternative and event permutations preserve result and fingerprints
- sparse episodes account for unrated pairs without enumerating them
- all qualifying pairs remain present; no transitive reduction occurs
- episode scale caps total weight at `12.0`
- one-edge episodes are not scaled
- source event IDs match effective set events exactly
- diagnostic pair counts reconcile exactly
- zero-edge result is typed `insufficient_evidence`
- invalid mixed episode, scale, unknown alternative, duplicate event ID,
  duplicate sequence, or invalid watermark fails closed
- no compiler code reads SQLite, environment, settings, HTTP form, or application tracker
- no solver, learned vector, activation, or ranking effect appears
- managed docs and generated metadata validate

## Non-Goals

- ask user direct Job A versus Job B questions
- persist current ratings or current edges
- create a preference-edge database table
- compile pairs across episodes
- infer edges from unrated alternatives
- infer equality from same-star ratings
- compile adjacent one-star differences under v1
- perform transitive reduction
- sample or truncate qualifying pairs
- learn gap weights
- train latent preference vector
- choose or import solver
- define optimizer margin, alpha, regularization, or evaluation gates
- create policy snapshots or activation events
- alter production ranking or `strong | stretch | skip`
- alter CV generation eligibility
- infer application history
- add settings UI or JavaScript
- backfill old runs

## Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| second reducer drifts from UI | one provenance reducer; existing value reducer becomes projection |
| adjacent ratings create noisy constraints | v1 minimum gap `2` |
| large rated episodes dominate | one episode budget scale capped at `12.0` |
| cap destroys gap ordering | multiply every edge by same episode scale |
| input order changes fingerprints | sort alternatives, effective states, and edges canonically |
| later rating contaminates old training snapshot | filter strictly through event watermark |
| source events cannot be audited | preserve exactly two effective set-event IDs per edge |
| equal ratings become false utility equality | omit pair; record equal diagnostic only |
| graph optimization removes evidence | no transitive reduction |
| compiler cache becomes stale truth | no persistence or cache; rebuild from ledger |
| policy leaks into runtime settings | strict policy file ownership and shadow rejection |
| quadratic pairs become expensive | episode set is bounded; standard-library O(n²) enumeration remains simplest correct path; revisit only with measured scale pressure |
| Phase 6 scope leaks early | no solver, training run, evaluation, or activation artifact |

## Validation Plan

- proof target: compiler policy has one owner
  - method: config tests and source search
  - evidence: exact policy block loads; no settings or env shadow exists
- proof target: reducer remains one SSOT
  - method: provenance and compatibility tests
  - evidence: UI values and compiler states derive from same latest-event selection
- proof target: pair algebra covers all ordinal cases
  - method: exhaustive table over `{unrated,1,2,3,4,5}²`
  - evidence: 36 cases match omission/orientation contract
- proof target: candidate set stays episode-bound
  - method: recompute Phase 4 canonical candidate-set fingerprint from alternatives
  - evidence: exact match passes; missing, extra, or changed alternative evidence fails closed
- proof target: compiler is symmetric
  - method: swap endpoints and input ordering
  - evidence: orientation changes only with rating ownership; weights and canonical result remain invariant
- proof target: compiler is deterministic
  - method: shuffled alternatives/events and repeated compilation
  - evidence: structurally equal result and identical fingerprints
- proof target: watermark replay is exact
  - method: compile before and after set/change/clear sequences
  - evidence: only events through watermark affect effective state and edges
- proof target: episode cap preserves evidence order
  - method: one-edge and over-budget episode tests
  - evidence: one-edge weights stay `2 < 3 < 4`; large episode total is capped
- proof target: every pair is accounted for
  - method: diagnostic reconciliation assertion
  - evidence: omitted plus emitted counts equal unordered pair count
- proof target: provenance is complete
  - method: inspect emitted edge event IDs
  - evidence: exactly two latest effective set-event IDs aligned with endpoints
- proof target: incompatible inputs fail closed
  - method: malformed episode/event/policy matrix
  - evidence: `ValueError`; no partial edge result
- proof target: Phase 4 behavior remains stable
  - method: config, decision-feedback, SQLite, store, app, pipeline, and parity regressions
  - evidence: existing suites pass unchanged
- proof target: Phase 5 remains compiler-only
  - method: dependency and source search
  - evidence: no DB table, route, worker, solver, learned vector, activation, or ranking use
- proof target: lifecycle docs remain source-derived
  - method: architecture sync/check, planning lifecycle, repo contracts, diff check
  - evidence: all validators pass and generated outputs are current

Recommended implementation verification:

```text
python -m pytest tests/test_config.py tests/test_decision_feedback.py -q
python -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_store.py -q -k "decision_feedback or admin_route_manifest"
python -m pytest tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py -q
python -m pytest tests/test_ranking.py tests/test_ranking_contract.py tests/test_ai_score.py -q
python -m ruff check src/fitcv/decision_feedback.py tests/test_decision_feedback.py
uvx mypy src/fitcv/decision_feedback.py --show-error-codes --follow-imports=skip
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
```

Expected: no solver, persistence, route, activation, learned-vector, or settings
surface in Phase 5 domain module.

## Completion Criteria

Phase 5 implementation is complete when:

1. all Key Deliverables and Acceptance Criteria pass
2. one policy file owns ordinal labels and compiler semantics
3. one canonical reducer owns effective rating and provenance
4. every unordered pair follows one symmetric decision table
5. unrated, equal, and below-gap pairs create no edge
6. every qualifying pair creates one directed edge
7. v1 gap weights and minimum gap are exact and versioned
8. one episode scale caps total evidence without normalizing every episode to one
9. source event IDs, watermark, input fingerprint, and edge-set fingerprint are replayable
10. zero-edge episodes return typed `insufficient_evidence`
11. malformed or incompatible input fails closed
12. Phase 4 UI, ledger, old-run behavior, and application-history separation remain unchanged
13. Phase 3 ranking, labels, CV behavior, and artifacts remain unchanged
14. no persistence, route, stage, worker, solver, learned vector, evaluation, activation, or new dependency exists
15. source docs and generated metadata are current
16. implementation plan is completed with fresh verification evidence
17. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/superpowers/specs/2026-07-14-22-25-fitcv-inverse-optimization-master-ssot-symmetry-spec.md`
- `docs/superpowers/specs/2026-07-16-00-19-fitcv-inverse-optimization-phase-4-decision-feedback-spec.md`
- `docs/superpowers/plans/2026-07-16-00-41-fitcv-inverse-optimization-phase-4-decision-feedback-plan.md`
- `config/policy/decision_learning.yaml`
- `src/fitcv/decision_feedback.py`
- `docs/operating_system/governance/repo-governance.md`
- `docs/operating_system/lifecycle/doc-system-lifecycle.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
