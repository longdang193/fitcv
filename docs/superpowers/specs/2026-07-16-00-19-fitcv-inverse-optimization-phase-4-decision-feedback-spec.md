---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: fitcv-inverse-optimization-phase-4-decision-feedback
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-stage-authority-contract
parent_spec: docs/superpowers/specs/2026-07-14-22-25-fitcv-inverse-optimization-master-ssot-symmetry-spec.md
targets:
  - config/policy/decision_learning.yaml
  - src/fitcv/config.py
  - src/fitcv/decision_feedback.py
  - src/fitcv/vector_search.py
  - src/fitcv/ranking_contract.py
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_context.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/store.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/run_detail_tab_enriched.html
  - docs/architecture.md
  - docs/configuration.md
  - docs/pipeline.md
  - docs/stages/ranking.source.yaml
  - docs/features/cv_system/feature.source.yaml
  - docs/features/admin_control_plane_core/feature.source.yaml
  - docs/features/inspection_debugging/feature.source.yaml
  - tests/test_config.py
  - tests/test_decision_feedback.py
  - tests/test_pipeline.py
  - tests/test_pipeline_stage_resume_parity.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_store.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - tests/test_fitcv_cp/test_app.py
related_features:
  - cv_system
  - admin_control_plane_core
  - inspection_debugging
related_stages:
  - ranking
---

# Detailed Spec: FitCV inverse optimization Phase 4 decision feedback

## Goal

Add one durable, append-only decision-feedback path for future explicit user judgment without fabricating application history, reconstructing old ratings, or adding optimization runtime.

Uniform flow:

```text
completed run with immutable ranking evidence
-> decision_feedback_source_v1
-> native 1–5-star POST or clear POST
-> canonical decision episode materialization
-> append-only rating event
-> deterministic effective rating
-> redirect to same enriched-review view
```

Ordinal scale:

```text
1 = definitely not interested
2 = low application interest
3 = might consider applying
4 = strong application interest
5 = would prioritize applying
```

Stars mean **personal application interest after eligibility**. They do not mean qualification, generic job quality, application completion, or cardinal utility.

Phase 4 captures evidence only. It does not compile pairwise constraints, train a latent vector, import CVXPY or NumPy, alter ranking order, or change `strong | stretch | skip`.

## Triage

- layer: `change`
- feature type: `ADD`
- parent: inverse-optimization master SSOT and symmetry specification
- dependencies: Phase 1, Phase 2, and Phase 3 implementations are complete
- affected stage: `ranking` as immutable evidence producer
- affected features: `cv_system`, `admin_control_plane_core`, `inspection_debugging`
- primary lens: mixed stage, persistence, and admin UI boundary
- generated refresh required: yes
- implementation code: out of scope for this document
- implementation plan: required after approval
- GitNexus: FTS index is degraded; current source, tests, config, and managed lifecycle documents are authoritative

## Current-State Diagnosis

Reusable owners:

- `config/policy/ranking.yaml` owns fixed ranking-v2 baseline
- `src/fitcv/ranking_contract.py` owns validated ranking contract identity
- `src/fitcv/vector_search.py` loads and validates exact job embeddings
- completed runs persist immutable `results_export_json`
- ranking rows preserve `raw_job_fingerprint`, `baseline_fit`, `baseline_fit_label`, and `ranking_contract_fingerprint`
- `PipelineRun.candidate_profile_json` preserves resolved candidate-profile snapshot
- `ControlPlaneStore` owns persistence delegation
- `_sqlite_connection(...)` owns SQLite connection and transaction setup
- enriched run-detail tab exposes larger review surface user browses
- `_safe_admin_redirect_target(...)` already validates admin redirect targets

Gaps:

- no canonical decision-learning policy
- no episode-ready immutable feedback source
- normalized job embeddings are not frozen in completed-run results
- no preference-context or qualification-context fingerprints
- no decision episode, alternative, or rating-event ledger
- no effective-rating owner
- no native rating controls or POST route
- old runs lack evidence required for safe rating
- owned SQLite connections do not enable foreign-key enforcement

Existing `application_tracker` is not rating truth. Phase 4 never reads it to infer interest and never writes it after a rating.

## Key Deliverables

### Deliverable 1: one versioned ordinal-rating policy

Create `config/policy/decision_learning.yaml` as sole Phase 4 owner of rating-scale version and labels. Add only fields Phase 4 uses. Compiler, solver, evaluation, and activation settings wait for owning phases.

### Deliverable 2: one immutable feedback-source artifact

Advance completed-run results from `results_job_ledger_v3` to `results_job_ledger_v4` and add one top-level `decision_feedback_source` block.

Freeze every evidence-complete scored alternative, not only final Top-N rows. User can rate a better choice found lower in scored review set.

### Deliverable 3: one canonical decision-episode identity

One canonical payload owns `episode_id`, database identity, materialization idempotency, conflict detection, and fingerprint tests. URL and title remain metadata. `raw_job_fingerprint` remains alternative identity.

### Deliverable 4: one append-only SQLite rating ledger

Use native SQLite tables, constraints, foreign keys, indexes, transactions, and append-only triggers. Same transaction path handles first rating, changes, and clear.

### Deliverable 5: one shared effective-rating reducer

```text
ordered rating events -> unrated | 1 | 2 | 3 | 4 | 5
```

Phase 5 reuses this reducer unchanged and adds comparison compilation. No second current-rating implementation.

### Deliverable 6: one native accessible star interface

Use HTML forms, submit buttons, labels, fieldsets, and CSS. No JavaScript for rating submission. Successful writes use redirect-after-POST and preserve validated filter, query, page, and page-size URL.

## Canonical Ownership

| Fact | Canonical owner |
| --- | --- |
| rating scale version and labels | `config/policy/decision_learning.yaml` |
| rating semantics, source construction, fingerprints, and validation | `src/fitcv/decision_feedback.py` |
| fixed baseline values and labels | Phase 3 ranking artifact |
| job embedding used for learning | immutable `decision_feedback_source_v1` alternative |
| preference scope | canonical preference-context fingerprint |
| qualification snapshot identity | canonical candidate-profile fingerprint |
| episode identity | canonical episode-payload fingerprint |
| raw user judgment | append-only `decision_rating_events` |
| effective current rating | shared deterministic reducer |
| persistence | `ControlPlaneStore` and SQLite implementation |
| HTTP validation and redirect | FastAPI boundary |
| rating display | enriched run-detail template |
| application status | separate application-history owner |

Derived fingerprints and UI projections are evidence, not competing mutable owners.

## Decision-Learning Policy Contract

```yaml
decision_learning_policy:
  policy_version: decision-learning-v1
  domain_id: ranking_v1
  rating_scale:
    version: application-interest-v1
    unrated_label: unrated
    labels:
      "1": definitely not interested
      "2": low application interest
      "3": might consider applying
      "4": strong application interest
      "5": would prioritize applying
```

Validation:

- policy exists in strict SSOT mode
- `policy_version`, `domain_id`, and scale `version` are nonempty
- `domain_id` is exactly `ranking_v1` in Phase 4
- labels contain exactly keys `"1"` through `"5"`
- every label is nonempty and unique after whitespace normalization
- `unrated_label` is exactly `unrated`
- unknown Phase 4 keys fail
- `.env.yaml` and other policy files cannot shadow policy
- code contains no copied production labels or version fallback

Control-plane settings do not expose this policy in Phase 4. Rating semantics are a versioned contract, not a per-run tuning control.

## Immutable Feedback-Source Contract

### Results-export schema

Completed-run results advance to `results_job_ledger_v4` and add:

```text
decision_feedback_source:
  schema_version: decision_feedback_source_v1
  domain_id
  run_id
  preference_context_version
  preference_context_fingerprint
  qualification_context_version
  qualification_context_fingerprint
  ranking_contract_fingerprint
  baseline_policy_fingerprint
  embedding_model
  embedding_dimension
  embedding_contract_fingerprint
  candidate_set_fingerprint
  source_stage_artifact_fingerprint
  alternatives[]
```

Alternative shape:

```text
alternative_id
displayed_rank
baseline_fit
baseline_fit_label
normalized_embedding
embedding_vector_fingerprint
source_job_url
shortlist_origin
```

### Inclusion rule

A row enters `alternatives` only when:

- it reached scoring through production scoring shortlist
- hard eligibility was satisfied
- `raw_job_fingerprint` is nonempty and unique
- `baseline_fit` is finite and within `[0, 1]`
- `baseline_fit_label` is `strong | stretch | skip`
- ranking and baseline-policy fingerprints resolve
- one finite nonzero job embedding resolves under exact run embedding contract
- normalized embedding dimension matches source contract

Include every evidence-complete scoring row, including `scored_not_ranked`. Exclude hard-gated jobs, pre-filter rejects, unscored jobs, invalid-embedding rows, and Phase 2 audit rows.

Phase 2 audit rows remain artifact-only and are not rescored in Phase 4. Later approved work may make them rateable only after producing same baseline and embedding evidence without leaking them into production ranking.

### Stable display order

`displayed_rank` enumerates complete source alternatives with Phase 3 order:

```text
descending baseline_fit
ascending raw_job_fingerprint
```

Production `baseline_rank` remains unchanged. `displayed_rank` is review order only.

### Context fingerprints

`preference_context_v1` hashes normalized effective preference scope:

```text
domain_id
target_role
role_families
domains
seniority_target
preferred_locations
work_modes
```

Lists are deduplicated and sorted. Empty values remain explicit. `preferred_locations` comes from the canonical Phase 1 candidate context. Candidate language inventory remains qualification context unless a later contract adds an explicit language preference. Entire mutable CV/profile is not hashed into preference context.

`qualification_context_v1` hashes exact canonical candidate-profile snapshot used by run. It preserves qualification context for replay but is not automatically a later training-cohort partition key.

`baseline_policy_fingerprint` derives from exact validated `ranking_policy`. It is not a second policy owner. `ranking_contract_fingerprint` still binds eligibility projection and executable ranking context.

### Embedding preservation

Feedback source stores full normalized vector used by future latent learning. It may resolve from live vector-search output or exact cached embedding evidence while run executes, but completed-run artifact contains the full normalized vector.

Vector evidence crosses into scoring through one explicit identity adapter. Existing vector search may continue to query by URL, but `_materialize_scoring_shortlist(...)` must require a one-to-one URL match, reject duplicate or ambiguous passed-job mappings, then attach `raw_job_fingerprint`, normalized vector, and vector fingerprint as one unit. Downstream source construction joins only by `raw_job_fingerprint`; URL remains metadata.

After completion, first rating:

- reads persisted feedback source only
- never regenerates embedding text
- never calls embedding provider
- never queries newer embedding row
- never recomputes baseline score or label

Full-run and resume paths emit byte-equivalent canonical feedback sources for identical evidence.

### Fingerprint algebra

Reuse `src/fitcv/shortlist_runtime.py::build_contract_fingerprint(...)`. Add no second hash implementation.

`embedding_vector_fingerprint` hashes normalized float list.

`candidate_set_fingerprint` hashes alternatives sorted by `(displayed_rank, alternative_id)` and includes:

```text
alternative_id
displayed_rank
baseline_fit
baseline_fit_label
embedding_vector_fingerprint
shortlist_origin
```

It excludes URL, title, and timestamps.

`source_stage_artifact_fingerprint` is master-spec field name for canonical `decision_feedback_source_v1` fingerprint. Payload excludes fingerprint field itself, URL metadata, and timestamps.

## Decision Episode Contract

### Domain records

`src/fitcv/decision_feedback.py` owns plain immutable records and validation. Use standard library only:

- `enum.IntEnum` for `RatingValue`
- `enum.StrEnum` for event type when supported by project Python floor
- frozen `dataclasses.dataclass` records
- existing canonical fingerprint helper
- `uuid.uuid4()` for event IDs
- timezone-aware UTC timestamps

Do not add repository abstraction. `ControlPlaneStore` is existing persistence boundary.

### Canonical episode payload

`episode_id` is SHA-256 of exactly:

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

Payload excludes URLs, titles, time, actor, and current rating. Same payload yields same episode. Any identity-field change yields another episode.

### Episode record

```text
episode_id
domain_id
run_id
preference_context_fingerprint
qualification_context_fingerprint
ranking_contract_fingerprint
embedding_contract_fingerprint
baseline_policy_fingerprint
embedding_model
embedding_dimension
rating_scale_version
candidate_set_fingerprint
source_stage_artifact_fingerprint
created_at
```

### Episode alternative record

```text
episode_id
alternative_id
displayed_rank
baseline_fit
baseline_fit_label
normalized_embedding_json
embedding_vector_fingerprint
source_job_url
shortlist_origin
created_at
```

Episode freezes complete candidate set. Rating POST cannot materialize one-row episode containing only clicked alternative.

## SQLite Contract

### Connection behavior

Add `PRAGMA foreign_keys=ON` to existing owned SQLite connection setup. Keep WAL, synchronous, busy-timeout, retry, and corruption recovery under current owner.

### Tables

Create tables on demand through one `_ensure_local_decision_feedback_tables(...)` helper.

#### `decision_episodes`

```text
episode_id TEXT PRIMARY KEY
domain_id TEXT NOT NULL
run_id TEXT NOT NULL
preference_context_fingerprint TEXT NOT NULL
qualification_context_fingerprint TEXT NOT NULL
ranking_contract_fingerprint TEXT NOT NULL
embedding_contract_fingerprint TEXT NOT NULL
baseline_policy_fingerprint TEXT NOT NULL
embedding_model TEXT NOT NULL
embedding_dimension INTEGER NOT NULL CHECK (embedding_dimension > 0)
rating_scale_version TEXT NOT NULL
candidate_set_fingerprint TEXT NOT NULL
source_stage_artifact_fingerprint TEXT NOT NULL
created_at TEXT NOT NULL
UNIQUE (episode_id, rating_scale_version)
```

#### `decision_episode_alternatives`

```text
episode_id TEXT NOT NULL
alternative_id TEXT NOT NULL
displayed_rank INTEGER NOT NULL CHECK (displayed_rank > 0)
baseline_fit REAL NOT NULL CHECK (baseline_fit >= 0 AND baseline_fit <= 1)
baseline_fit_label TEXT NOT NULL CHECK (baseline_fit_label IN ('strong', 'stretch', 'skip'))
normalized_embedding_json TEXT NOT NULL
embedding_vector_fingerprint TEXT NOT NULL
source_job_url TEXT NOT NULL
shortlist_origin TEXT NOT NULL
created_at TEXT NOT NULL
PRIMARY KEY (episode_id, alternative_id)
UNIQUE (episode_id, displayed_rank)
FOREIGN KEY (episode_id) REFERENCES decision_episodes(episode_id)
```

#### `decision_rating_events`

```text
event_sequence INTEGER PRIMARY KEY
event_id TEXT NOT NULL UNIQUE
episode_id TEXT NOT NULL
alternative_id TEXT NOT NULL
event_type TEXT NOT NULL CHECK (event_type IN ('set_rating', 'clear_rating'))
rating INTEGER
rating_scale_version TEXT NOT NULL
acted_by TEXT NOT NULL
created_at TEXT NOT NULL
CHECK (
  (event_type = 'set_rating' AND rating BETWEEN 1 AND 5)
  OR
  (event_type = 'clear_rating' AND rating IS NULL)
)
FOREIGN KEY (episode_id, alternative_id)
  REFERENCES decision_episode_alternatives(episode_id, alternative_id)
FOREIGN KEY (episode_id, rating_scale_version)
  REFERENCES decision_episodes(episode_id, rating_scale_version)
```

Indexes:

```text
decision_episodes(run_id, created_at)
decision_rating_events(episode_id, alternative_id, event_sequence)
```

Create native `BEFORE UPDATE` and `BEFORE DELETE` abort triggers for all three tables. No repository update or delete method exists.

### Atomic write

One SQLite transaction handles every rating command:

1. begin immediate transaction
2. ensure tables
3. insert episode when absent
4. when present, verify every identity field
5. insert complete alternative set when episode is new
6. when alternatives exist, verify count, ranks, scores, labels, vector fingerprints, and source fingerprint
7. verify target alternative belongs to episode
8. append one rating event
9. commit

Any failure rolls back episode, alternatives, and event. Concurrent first writes serialize through SQLite; both valid actions may append separate events to same canonical episode.

## Store Boundary Contract

Add only Phase 4 methods:

```text
materialize_episode_and_append_rating(episode, alternatives, event)
list_decision_rating_events_for_run(run_id)
```

`ControlPlaneStore` delegates both and preserves existing optional-function test injection. SQLite is only supported Phase 4 backend. Future backend without equivalent atomicity, constraints, and replay tests fails explicitly on POST. No process-memory fallback.

## Effective Rating Contract

`reduce_rating_events(...)` accepts stored events ordered by:

```text
episode_id
alternative_id
event_sequence
```

For each `(episode_id, alternative_id)`:

- no event -> `unrated`
- latest `set_rating` -> exact `1 | 2 | 3 | 4 | 5`
- latest `clear_rating` -> `unrated`

SQLite assigns monotonic `event_sequence`; timestamps and UUID event IDs remain audit metadata and never decide current state. Reducer does not infer missing events, average ratings, collapse ordinal scale, or interpret stars as numeric utility. Malformed persisted events fail validation instead of being skipped.

## HTTP Boundary Contract

### Route

```text
POST /admin/runs/{run_id}/decision-feedback/{alternative_id}
```

Native fields:

```text
rating: "1" | "2" | "3" | "4" | "5" | absent
action: "clear_rating" | absent
rating_scale_version
source_stage_artifact_fingerprint
return_to
```

Exactly one command is valid:

- rating present and action absent -> `set_rating`
- action is `clear_rating` and rating absent -> `clear_rating`

Boundary behavior:

- unknown run -> `404`
- unsupported or missing source artifact -> `409`
- unknown alternative -> `404`
- invalid command, rating, missing scale, or unknown submitted scale -> `422`
- stale source fingerprint, valid-but-conflicting scale, or incompatible episode -> `409`
- unsupported persistence backend -> `501`
- valid write -> `303`

`acted_by` comes from server-owned admin principal resolver. Current local single-user mode may return code-owned `local_operator`; form input never owns actor identity.

### Safe redirect

Reuse `_safe_admin_redirect_target(...)`, then require normalized path to equal same run's enriched tab:

```text
/admin/runs/{run_id}/tabs/enriched
```

Query may preserve page, page size, filter, search, and pipeline outcomes. Scheme, netloc, another run ID, or another admin path falls back to same run's default enriched URL.

### GET behavior

GET remains read-only:

- no episode creation
- no event append
- no old-run backfill
- no current embedding or ranking query to manufacture evidence

Enriched-tab context joins alternatives and effective ratings by `raw_job_fingerprint`.

## Native 1–5-Star UI Contract

Enriched table adds `Application interest` column.

Each source alternative renders one native form containing:

- `<fieldset>` and `<legend>`
- five submit buttons named `rating`
- accessible label from decision-learning policy
- clear button when rated
- hidden rating-scale version
- hidden source fingerprint
- hidden validated return URL

CSS may render filled and unfilled stars. DOM order stays `1` through `5`. Keyboard focus and visible focus remain native.

Visible copy:

```text
Rate personal application interest after eligibility. This does not record an application.
```

No JavaScript is required for set, change, or clear. Rows absent from source show no active form. Old v3 runs show one bounded explanation that rating evidence was not captured.

## Admissible-Case Matrix

| Case | Artifact | Persistence | Effective state | HTTP/UI |
| --- | --- | --- | --- | --- |
| completed v4 run, no ratings | valid source | no episode | unrated | controls visible |
| first valid rating | unchanged source | episode, all alternatives, event atomically inserted | selected rating | `303` |
| second rating | unchanged source | event appended | newest rating | `303` |
| clear after rating | unchanged source | clear appended | unrated | `303` |
| clear while unrated | unchanged source | clear appended | unrated | `303` |
| repeated same rating | unchanged source | every event retained | same rating | `303` |
| equal timestamps | unchanged source | events retained | greater event sequence wins | deterministic |
| lower scored row | valid alternative | event appended | selected rating | supported |
| old v3 run | no source | no rows | unavailable | read-only explanation |
| missing embedding | row excluded | no rows | unavailable | no control |
| hard eligibility failure | row excluded | no rows | unavailable | no control |
| Phase 2 audit row | audit only | no rows | unavailable | no control |
| invalid rating | unchanged source | rollback/no rows | unchanged | `422` |
| rating and clear supplied | unchanged source | rollback/no rows | unchanged | `422` |
| unknown alternative | unchanged source | rollback/no rows | unchanged | `404` |
| stale source fingerprint | unchanged source | rollback/no rows | unchanged | `409` |
| malformed or unknown submitted scale | unchanged source | rollback/no rows | unchanged | `422` |
| valid scale conflicts with source or episode | unchanged source | rollback/no rows | unchanged | `409` |
| duplicate alternative IDs | invalid source | no rows | unavailable | controls suppressed |
| nonfinite score or vector | invalid source row | no rows | unavailable | controls suppressed |
| concurrent first ratings | one source | one episode, both events | deterministic latest | no duplicate episode |
| existing episode mismatch | retained source | rollback/no event | unchanged | `409` |
| unsafe external redirect | unchanged source | valid event may append | updated | same-run fallback |
| unsupported backend | unchanged source | no fallback | unchanged | `501` |
| application tracker exists | unchanged source | separate ledgers | rating only | no inference |

## Task/Wave Breakdown

### Wave 1: freeze policy and feedback source

**Purpose:** establish rating semantics and immutable episode input.

**Steps:**

- [ ] add failing config tests for one canonical Phase 4 policy subset
- [ ] add source tests for every inclusion and exclusion case
- [ ] define preference, qualification, baseline-policy, vector, candidate-set, source, and episode fingerprints
- [ ] prove source order is permutation-invariant and matches Phase 3
- [ ] prove full-run and resume source parity

**Verification:**

- [ ] one v4 source contains all and only evidence-complete scored rows
- [ ] v3 runs remain readable and never backfilled

**Exit Criteria:** episode materialization consumes one immutable validated source.

### Wave 2: add records and append-only persistence

**Purpose:** persist ordinal evidence through one transaction and one ledger.

**Steps:**

- [ ] add enums, frozen records, source construction, validation, fingerprints, and reducer before pipeline wiring
- [ ] enable SQLite foreign keys
- [ ] add tables, constraints, indexes, and append-only triggers
- [ ] add atomic episode materialization plus event append
- [ ] add ordered event listing for one run
- [ ] add store delegation and unsupported-backend behavior

**Verification:**

- [ ] first write is atomic
- [ ] set and clear append without update-in-place
- [ ] constraints reject malformed events and unknown alternatives

**Exit Criteria:** raw evidence is durable and optimizer-independent.

### Wave 3: add native HTTP and star surface

**Purpose:** capture low-friction feedback without pairwise questions or custom UI state.

**Steps:**

- [ ] add one validated POST route
- [ ] reuse same-run safe redirect
- [ ] join source alternatives and reduced ratings into enriched context
- [ ] render accessible five-button stars and clear action
- [ ] keep GET read-only
- [ ] show explicit semantics and application-history separation

**Verification:**

- [ ] set, change, clear, invalid, stale, unknown, and unsafe-redirect tests pass
- [ ] template requires no JavaScript and preserves accessibility basics

**Exit Criteria:** user can rate every evidence-complete scored alternative.

### Wave 4: reconcile lifecycle truth

**Purpose:** align managed docs, artifacts, and tests with Phase 4 behavior.

**Steps:**

- [ ] add capability metadata for feedback source and ordinal ledger
- [ ] update ranking stage source without claiming ranking consumes ratings
- [ ] update architecture, configuration, and pipeline docs
- [ ] regenerate managed stage, feature, lineage, history, and discovery outputs
- [ ] run focused, parity, structural, lifecycle, and repo validation

**Verification:**

- [ ] generated surfaces derive from source and metadata
- [ ] no compiler, solver, activation, or ranking-runtime scope leaked

**Exit Criteria:** implementation-ready and bounded for Phase 5 handoff.

## Design Decisions

### Decision: results export owns episode-ready source

- context: stage artifacts contain bounded samples, not every scored alternative
- choice: add full `decision_feedback_source_v1` to immutable completed results
- alternatives: first-rating reconstruction; mutable current-feedback table
- impact: old evidence cannot drift; rating POST performs no model or ranking work

### Decision: every scored row is reviewable

- context: user often finds better choices below final list
- choice: include all evidence-complete production scoring rows in stable baseline order
- alternatives: final Top-N only; every enriched row regardless of evidence
- impact: feedback matches browsing while hard-gated and unscored rows remain excluded

### Decision: Phase 2 audit rows remain unrated

- context: Phase 2 keeps audit rows out of AI scoring/ranking, while episode alternatives require baseline evidence
- choice: preserve audit isolation until separately approved equivalent evidence exists
- alternatives: silently score in rating route; store context-free rating
- impact: no Phase 2 invariant breaks; retrieval-recall learning stays later work

### Decision: rating policy starts narrow

- context: later phases need compiler and solver settings, Phase 4 does not
- choice: create rating-scale keys only and extend policy in owning phases
- alternatives: scaffold every future setting
- impact: one SSOT without dead config

### Decision: one reducer begins in Phase 4

- context: UI needs current state before Phase 5
- choice: add deterministic reducer now; Phase 5 reuses it
- alternatives: mutable current column; UI-only reduction
- impact: raw events remain sole truth

### Decision: database enforces append-only evidence

- context: repository conventions cannot prevent accidental update/delete
- choice: native SQLite triggers plus no update/delete methods
- alternatives: comments and discipline
- impact: raw evidence cannot be silently rewritten

### Decision: one route handles set and clear

- context: separate endpoints add no semantic value
- choice: one boundary validates exactly one command
- alternatives: endpoint per star and separate clear endpoint
- impact: smaller HTTP surface and one transaction path

### Decision: old runs stay unrated

- context: old artifacts lack frozen vectors and context fingerprints
- choice: read-only unavailability, never backfill
- alternatives: recompute current evidence
- impact: historical truth stays honest

### Decision: no generic feedback framework

- context: ranking is first concrete domain
- choice: concrete records plus existing config/store/UI boundaries
- alternatives: plugin protocol, event bus, ORM, repository hierarchy
- impact: minimum surface; abstraction waits for second domain

## Invariants

1. `config/policy/decision_learning.yaml` is only Phase 4 rating-scale owner.
2. Code owns allowed names, types, ranges, validation, and fingerprint semantics.
3. Stars mean personal application interest after eligibility.
4. Stars do not mean qualification, application status, or cardinal utility.
5. Every rating action is append-only evidence.
6. No mutable `current_rating`, JSON shadow, or UI cache exists.
7. Effective rating derives through one shared reducer.
8. Clear reduces to unrated and never deletes history.
9. GET never creates episode or event.
10. First rating atomically materializes complete compatible episode.
11. One canonical payload owns episode ID everywhere.
12. `raw_job_fingerprint` is alternative identity.
13. URL and title are metadata only.
14. Application history is never inferred from ratings.
15. Ratings never create or update application-history rows.
16. Old runs are never backfilled.
17. Completed v4 feedback sources are immutable.
18. Baseline score and label are copied, never recomputed on POST.
19. Normalized vectors are copied, never regenerated on POST.
20. Alternatives share one ranking, baseline, embedding, preference, and qualification context.
21. Every evidence-complete scored row is included regardless of final Top-N.
22. Hard-gated, unscored, invalid-vector, and audit rows are excluded.
23. `displayed_rank` follows Phase 3 order but has no production authority.
24. Vector evidence does not affect Phase 4 score, label, or tie-break.
25. Phase 4 changes no `strong | stretch | skip` behavior.
26. Phase 4 performs no pairwise compilation.
27. Phase 4 imports no CVXPY, NumPy, or solver package.
28. SQLite foreign keys are enabled on owned connections.
29. Constraints reject malformed events and unknown alternatives.
30. Triggers reject update/delete on feedback evidence.
31. Set, change, and clear use one transaction path.
32. Invalid HTTP input fails before persistence.
33. Successful POST uses `303` to validated same-run enriched URL.
34. Actor identity is server-owned.
35. Unsupported backends fail explicitly; no memory fallback.
36. Full-run and resume produce equivalent feedback sources.
37. No second fingerprint implementation is added.
38. No ORM, migration framework, JS state framework, event bus, plugin framework, or speculative repository hierarchy is added.

## Acceptance Criteria

- strict config requires one valid Phase 4 decision-learning policy
- shadow policy keys fail at config boundary
- exact five labels and unrated semantics agree across config, domain, UI, and tests
- completed results use `results_job_ledger_v4`
- v4 results include one canonical `decision_feedback_source_v1`
- source includes all evidence-complete scoring rows, including below final Top-N
- hard-gated, unscored, invalid-vector, and audit rows are absent
- context, policy, vector, candidate-set, source, and episode fingerprints are deterministic and permutation-invariant
- same episode payload materializes one database episode
- changed identity field yields another episode
- first rating inserts episode, all alternatives, and event atomically
- rating change appends second event and preserves first
- clear appends event and reduces state to unrated
- SQL constraints reject invalid rating and unknown alternative
- SQL triggers reject update and delete
- reducer covers no event, set, change, clear, repeated values, and equal timestamps
- native forms work without JavaScript
- every star button has accessible name with value and exact label
- successful actions preserve validated enriched-tab state
- unsafe redirects fall back to same run
- old v3 runs remain readable but cannot be rated
- no application history is synthesized or modified
- no optimizer, compiler, learned vector, activation, or ranking-runtime behavior exists

## Non-Goals

- reconstruct unrecorded ratings or applications
- infer application from rating, viewing, shortlist, rank, or CV generation
- ask repeated mandatory pairwise questions
- treat stars as cardinal utility or average them
- compile pairwise constraints
- define clear gaps or episode budgets
- train or evaluate latent preference vector
- add CVXPY, NumPy, or solver dependencies
- add learned alpha, optimizer, solver, evaluation, or activation config
- apply learned preference at runtime
- change baseline score, order, labels, or CV eligibility
- rate hard-gated, unscored, or Phase 2 audit rows
- expose rating scale in admin settings
- backfill old runs
- add user accounts, multi-tenant authorization, or new authentication
- replace current control-plane trust boundary
- add ORM, migration framework, repository hierarchy, UI state framework, event bus, plugin system, or generic feedback protocol
- publish private operating-system artifacts

## Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| stars mistaken for qualification | exact interest labels and visible explanation |
| stars mistaken for application history | separate ledgers; no inference or cross-write |
| lower-ranked useful jobs cannot be rated | include every evidence-complete scoring row |
| historical evidence drifts | freeze v4 source; no first-rating recomputation |
| old runs appear rateable | explicit unavailable state; no backfill |
| event history is rewritten | append-only triggers and no mutation methods |
| first rating leaves partial episode | one immediate transaction |
| concurrent first writes duplicate episode | canonical ID, serialization, conflict verification |
| stale page rates changed artifact | hidden source fingerprint check |
| redirect escapes admin page | safe helper plus same-run path restriction |
| vectors bloat generic artifacts | full vectors only in bounded feedback source; no stage samples |
| audit isolation breaks | audit rows remain unrated until approved evidence contract |
| future backend drops evidence | explicit unsupported error; no memory fallback |
| Phase 5 creates second reducer | Phase 4 reducer is inherited SSOT |
| policy becomes future scaffold | reject unknown keys; later phases add owned keys |

## Validation Plan

- proof target: one rating-semantics owner
  - method: config tests and source search
  - evidence: only decision-learning policy owns production labels/version
- proof target: source is complete and bounded
  - method: final-ranked, scored-not-ranked, unscored, hard-gated, invalid-vector, and audit fixtures
  - evidence: exact alternatives and display ranks
- proof target: historical evidence is frozen
  - method: mutate profile, ranking config, and embedding cache after completion, then rate
  - evidence: episode equals persisted source
- proof target: identity is permutation-invariant
  - method: shuffle jobs and mappings
  - evidence: candidate-set, source, and episode fingerprints unchanged
- proof target: full-run and resume are symmetric
  - method: complete equivalent runs from start and checkpoints
  - evidence: byte-equivalent feedback source
- proof target: first write is atomic
  - method: inject failure after episode insert and during alternatives/event insert
  - evidence: no partial rows
- proof target: evidence is append-only
  - method: set, change, clear, direct update, direct delete
  - evidence: events retained; mutations abort
- proof target: reducer is deterministic
  - method: repeated values, clears, equal timestamps, monotonic event sequences, shuffled groups
  - evidence: exact `unrated | 1..5`
- proof target: database owns structural validity
  - method: direct SQL invalid rating, missing alternative, scale mismatch, duplicate rank, invalid baseline
  - evidence: native constraint or FK failure
- proof target: HTTP rejects malformed commands
  - method: invalid values, both/neither commands, unknown alternative, stale fingerprint, unsafe redirect
  - evidence: exact status and no event
- proof target: UI is accessible without JavaScript
  - method: HTML assertions and direct POST
  - evidence: fieldset, legend, five labels, clear, focus, `303`
- proof target: old runs remain honest
  - method: render v3 and attempt POST
  - evidence: explanation, no controls, `409`, no rows
- proof target: application and rating stay separate
  - method: precreate tracker rows then rate
  - evidence: tracker unchanged; no inferred rating
- proof target: Phase 4 stays bounded
  - method: dependency/import/source search
  - evidence: no compiler, optimizer, solver, vector activation, new dependency, or settings control
- proof target: lifecycle docs are source-derived
  - method: architecture sync/check, planning lifecycle, repo contracts, diff check
  - evidence: validators pass and generated outputs are current

Focused implementation verification:

```text
python -m pytest tests/test_config.py tests/test_decision_feedback.py
python -m pytest tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py
python -m pytest tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_sqlite_store.py
python -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py
python scripts/hooks/run_validator.py --fast
python scripts/generate_planning_lineage.py
python tools/docs/generate_architecture_metadata.py --check
python scripts/validate_planning_lifecycle.py
python scripts/validate_repo_contracts.py --fast
git diff --check
```

## Completion Criteria

Phase 4 implementation is complete when:

1. all Key Deliverables and Acceptance Criteria pass
2. one narrow policy owns exact ordinal semantics
3. completed v4 runs preserve one immutable feedback source
4. every evidence-complete scoring row can be rated, including below final Top-N
5. old runs remain unmodified and explicitly unrated
6. one canonical payload owns episode identity and idempotency
7. first rating atomically persists episode, alternatives, and event
8. set, change, and clear append raw evidence
9. one reducer owns effective rating for UI and Phase 5
10. native accessible stars work without JavaScript
11. safe redirect preserves enriched-review state
12. application history remains separate and uninferred
13. full-run and resume parity passes
14. no compiler, optimizer, learned vector, activation, ranking change, or dependency exists
15. managed feature, stage, lineage, history, and discovery outputs are current
16. implementation plan is completed with fresh verification evidence

Canonical source-of-truth:

<LINK>
- `docs/superpowers/specs/2026-07-14-22-25-fitcv-inverse-optimization-master-ssot-symmetry-spec.md`
- `docs/superpowers/specs/2026-07-15-19-01-fitcv-inverse-optimization-phase-2-vector-only-shortlist-spec.md`
- `docs/superpowers/specs/2026-07-15-21-16-fitcv-inverse-optimization-phase-3-ranking-v2-baseline-spec.md`
- `docs/operating_system/governance/repo-governance.md`
- `docs/operating_system/lifecycle/doc-system-lifecycle.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
