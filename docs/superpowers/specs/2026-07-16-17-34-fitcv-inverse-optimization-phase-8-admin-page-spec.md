---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: fitcv-inverse-optimization-phase-8-admin-page
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-stage-authority-contract
targets:
  - config/policy/decision_learning.yaml
  - pyproject.toml
  - requirements.txt
  - Dockerfile
  - docker-compose.yml
  - src/fitcv/inverse_optimization.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/optimization_service.py
  - src/fitcv_cp/store.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/templates/base.html
  - src/fitcv_cp/templates/optimization.html
  - scripts/run_inverse_optimization.py
  - tests/test_inverse_optimization.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_optimization_page.py
  - tests/test_fitcv_cp/test_optimization_service.py
  - tests/test_fitcv_cp/test_store.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - docs/architecture.md
  - docs/configuration.md
  - docs/usage.md
  - docs/features/admin_control_plane_core/feature.source.yaml
  - docs/features/cv_system/feature.source.yaml
  - docs/features/inspection_debugging/feature.source.yaml
  - docs/features/ui_consistency_theming/feature.source.yaml
related_features:
  - admin_control_plane_core
  - cv_system
  - inspection_debugging
  - ui_consistency_theming
related_stages:
  - ranking
---

# Detailed Spec: FitCV inverse optimization Phase 8 admin page

## Goal

Add one user-facing admin page that lets an operator run and manage inverse
optimization without using terminal commands or preparing JSON files.

The page is a thin boundary over existing Phase 4-7 contracts. It must not
reimplement solver math, rating reduction, preference compilation, evaluation,
policy persistence, activation, rejection, rollback, or fingerprint logic.

Canonical flow:

```text
SQLite decision evidence
-> canonical store request loader
-> shared candidate orchestration
-> existing inverse solver and evaluation
-> existing immutable training/snapshot/event tables
-> HTML view model
-> native form actions
```

CLI and UI remain symmetric:

```text
JSON bundle -> CLI adapter ----                              -> shared candidate orchestration -> same result
SQLite evidence -> UI adapter -/
```

The first implementation optimizes only the canonical `ranking_v1` domain,
runs synchronously through a native HTML POST, and keeps all optimizer parameters
read-only. Background execution, simulation, multi-domain selection, and policy
parameter editing wait for measured need.

## Triage

- layer: `change`
- feature type: `ADD`
- parent: inverse-optimization master SSOT and symmetry specification
- dependencies: completed Phases 4, 5, 6, and 7
- affected stage: `ranking` policy lifecycle only
- affected features: `admin_control_plane_core`, `cv_system`,
  `inspection_debugging`, `ui_consistency_theming`
- implementation plan required after approval: yes

## Current State

Implemented owners already exist:

- `config/policy/decision_learning.yaml` owns optimizer, compiler, evaluation,
  and activation policy
- `src/fitcv/inverse_optimization.py` owns request validation, solve, independent
  numeric validation, held-out evaluation, diagnostics, and typed results
- `scripts/run_inverse_optimization.py` owns JSON CLI parsing and commands:
  `train`, `evaluate`, `candidate`, `reject`, `activate`, `rollback`,
  and `inspect`
- `ControlPlaneStore` and SQLite own immutable training runs, policy snapshots,
  activation events, evidence heads, candidate activation, rejection, and rollback
- the admin control plane already has shared navigation, cards, tables, forms,
  badges, validation errors, and redirect-after-POST patterns

Missing surface:

- no `/admin/optimization` route
- no optimization template or navigation entry
- no native form that builds a candidate from current stored rating evidence
- no UI for inspecting candidate metrics or lifecycle history
- no UI for activation, rejection, or rollback
- candidate orchestration remains private inside the CLI script
- current Docker image does not install the existing `inverse-optimization`
  optional dependency extra

## Key Deliverables

### Deliverable 1: one native optimization page

Add `GET /admin/optimization` with one page titled **Preference Optimization**
and navigation label **Optimization**.

The page uses existing `base.html` tokens and components. Core use requires no
JavaScript.

### Deliverable 2: one store-backed optimization action

Add **Optimize Current Evidence**. The user does not upload or edit JSON.

The action loads immutable decision episodes and rating events for
`ranking_v1`, builds the canonical `InverseOptimizationRequest`, runs the
existing candidate operation, persists the typed result, and redirects back to
the page.

### Deliverable 3: one shared candidate orchestration boundary

Extract candidate orchestration from `scripts/run_inverse_optimization.py` into
one small function module, `src/fitcv_cp/optimization_service.py`.

The module contains functions, not a service class, factory, interface hierarchy,
or command framework. CLI and HTTP call the same candidate function.

### Deliverable 4: complete manual lifecycle controls

Expose existing lifecycle operations:

- activate eligible candidate
- reject candidate with required reason
- rollback active policy to a prior compatible learned snapshot
- rollback active policy to canonical zero residual
- inspect training runs, snapshots, and activation events

Every mutation preserves existing compare-and-swap, provenance, evidence-head,
transaction, and append-only event contracts.

### Deliverable 5: honest empty, insufficient, conflict, and failure states

The page must render useful typed states for:

- empty database
- episodes with no ratings
- ratings with no compiled preference edges
- only one evidence episode
- candidate created
- no-op or insufficient evidence
- solver unavailable or solver failure
- stale evidence
- stale parent or concurrent mutation
- candidate rejected or stale
- active learned policy
- active zero residual
- rollback conflict

No case may produce a blank page, raw traceback, or ambiguous success message.

### Deliverable 6: solver-ready control-plane image

Use the existing `pyproject.toml` optional dependency as SSOT. Replace the
Docker editable-install command exactly with
`RUN pip install -e ".[inverse-optimization]"`; remove `--no-deps` and do not
copy the CVXPY version into `requirements.txt` or Dockerfile.

## Canonical Ownership

| Fact or behavior | Canonical owner |
| --- | --- |
| rating labels and optimizer parameters | `config/policy/decision_learning.yaml` |
| raw rating history | append-only `decision_rating_events` |
| effective ratings and pairwise edges | existing Phase 4-5 reducers/compiler |
| solver and evaluation behavior | `src/fitcv/inverse_optimization.py` |
| candidate orchestration | `src/fitcv_cp/optimization_service.py` |
| current evidence request loading | `ControlPlaneStore` / SQLite implementation |
| immutable candidate and lifecycle truth | existing training, snapshot, and event tables |
| CLI serialization | `scripts/run_inverse_optimization.py` |
| HTTP validation and redirect | `src/fitcv_cp/app.py` |
| display projection | `optimization.html` context only |

The page is not a policy editor. HTML fields, query strings, form payloads, and
flash messages are boundary data, not source truth.

## User Experience Contract

### Page section 1: Current Status

Show:

- domain: `ranking_v1`
- current policy mode: `zero residual`, `learned active`, or `incompatible`
- active snapshot ID when learned policy is active
- evidence episode count
- rating-event count
- event watermark
- decision-learning policy fingerprint
- optimizer policy fingerprint
- runtime contract fingerprint

Long fingerprints use `<code>` and may be visually truncated while retaining
full value in title or details text.

### Page section 2: Optimize Current Evidence

Show one primary form:

- domain: hidden canonical `ranking_v1`
- evidence-head fingerprint: hidden compare token
- expected parent reference: hidden compare token

Candidate creation has no actor field. It is content-addressed evidence processing,
not a lifecycle action.
- submit button: **Optimize Current Evidence**

Display helper text:

> Uses saved 1-5-star application-interest ratings. Creates a candidate only;
> it never activates automatically.

When the database contains zero episodes or zero rating events, render the button
disabled and explain what evidence is missing. Server-side validation remains
authoritative if a disabled form is bypassed.

### Page section 3: Rating Evidence

Render one read-only table from the same typed inverse-optimization request used
for optimization. Reduce append-only rating events through the canonical shared
reducer; do not copy ratings into a page-specific ledger.

Show only alternatives with an effective 1-5-star application-interest rating,
newest rating first, limited to 50 rows. Each row shows:

- effective rating time
- run link
- canonical job link
- saved baseline rank
- saved baseline fit and baseline label
- effective ordinal 1-5-star rating

Historical personalized rank is omitted because its learned-policy context may not
match the current page. The table is evidence inspection only: no duplicate rating
controls, mutation endpoint, JavaScript state, or page-owned cache is allowed.

### Page section 4: Latest Candidate

If a candidate exists, show:

- candidate status
- snapshot ID
- parent policy reference
- evidence watermark and fingerprint
- solver name and status
- episode and compiled-edge counts
- candidate versus baseline metrics
- candidate versus parent metrics when compatible
- vector norm and configured bound
- coverage summary
- retrieval-audit availability
- activation eligibility or blocking reason codes

Actions:

- **Activate Candidate** only when current stored state permits activation
- **Reject Candidate** with required reason

Activation and rejection forms include snapshot ID and current compare tokens.
The UI may hide an impossible action, but server-side lifecycle validation remains
mandatory.

### Page section 5: Active Policy and Rollback

Show active learned snapshot or canonical zero residual.

Rollback form:

- actor: required
- expected active reference: hidden compare token
- target: native `<select>` containing prior learned snapshots marked rollback-eligible
  by the store plus `zero_residual`
- required native confirmation checkbox
- submit button: **Rollback Policy**

### Page section 6: History

Render existing lifecycle inspection data in three compact tables:

1. training runs
2. policy snapshots
3. activation events

Newest rows display first. The store applies native SQL descending order and a
limit of 25 per table for this page; CLI inspection keeps its existing unbounded
behavior. No new history table or copied audit ledger is allowed.

## HTTP Contract

| Method | Route | Purpose | Success behavior |
| --- | --- | --- | --- |
| GET | `/admin/optimization` | render current evidence, active policy, candidate, and history | `200` HTML |
| POST | `/admin/optimization/candidate` | optimize current stored evidence and persist attempt | `303` to page |
| POST | `/admin/optimization/candidates/{snapshot_id}/activate` | activate candidate using existing CAS checks | `303` to page |
| POST | `/admin/optimization/candidates/{snapshot_id}/reject` | reject candidate with reason | `303` to page |
| POST | `/admin/optimization/rollback` | rollback to learned snapshot or zero residual | `303` to page |

Rules:

- all mutations use redirect-after-POST
- no route accepts optimizer numeric parameters
- domain input is fixed to `ranking_v1` and validated server-side
- snapshot and parent identifiers are opaque strings validated against store truth
- actor is required and whitespace-normalized for activation, rejection, and rollback
- rejection reason is required and bounded
- raw exception text is never placed in query strings or HTML
- typed notice codes may be placed in redirect query parameters

## Shared Application Boundary

### Candidate function

Add one public function in `src/fitcv_cp/optimization_service.py` with semantic
shape:

```python
create_ranking_policy_candidate(
    request: InverseOptimizationRequest,
    *,
    store: ControlPlaneStore,
    config: dict[str, Any],
    expected_evidence_head_fingerprint: str | None = None,
    expected_parent_ref: str | None = None,
) -> dict[str, Any]
```

Submitted compare tokens are passed to this function. CLI derives them from its
request and current parent; HTTP passes the hidden values rendered by the GET page.
The function rejects mismatches before solving and rechecks them before persistence.

It owns the current candidate orchestration now embedded in the CLI:

- validate current decision-learning policy
- verify request evidence head against current store evidence
- resolve compatible parent
- solve and evaluate candidate
- build immutable training and snapshot rows
- recheck evidence, parent, config, runtime, and optimizer provenance
- persist attempt atomically
- return existing typed result payload

It does not own JSON parsing, HTML rendering, SQL, or solver math.

### Store request loader

Add one store method with semantic shape:

```python
load_inverse_optimization_request(domain_id: str) -> InverseOptimizationRequest
```

SQLite implementation must derive full domain objects from existing decision
feedback tables. Refactor shared row loading so evidence-head fingerprinting and
request loading read one canonical row set instead of maintaining two drifting
SQL implementations.

The request loader:

- preserves episode, alternative, and event order deterministically
- sets `event_watermark` from the same event sequence boundary as the evidence
  head
- includes full `run_id`, URL, actor, and timestamps required by domain types
- sets `evaluation_context=None` for every Phase 8 store-loaded episode because
  no canonical persisted evaluation-context owner exists
- never searches run artifacts or invents location, language, retrieval, or relevance evidence

Missing evaluation context remains an honest `unknown` / `not_available`
result under existing Phase 6 behavior. Persisting evaluation context is separate
future scope.

### CLI parity

The CLI keeps its current JSON contract. `train` and `evaluate` remain pure
file-boundary commands. `candidate` parses the supplied bundle and calls the
same shared candidate function used by the page.

No CLI subprocess is launched from the web route.

## Result Presentation Contract

The page renders existing typed statuses; it does not create a second lifecycle
vocabulary.

Status groups:

- success: candidate created, activation completed, rejection completed, rollback completed
- information: no-op accepted, zero residual active
- warning: insufficient evidence, stale evidence, stale candidate, incompatible parent
- conflict: active snapshot changed, evidence head changed, concurrent activation
- error: invalid input, solver unavailable, solver failure, persistence failure

One server-side view helper maps typed status/reason codes to badge class and
human text. Templates must not reproduce status mapping branches in multiple
sections.

## Task/Wave Breakdown

### Wave 1: shared evidence and candidate boundary

**Purpose:**
- make CLI and UI consume the same application operation

**Steps:**
- [ ] extract candidate orchestration into one function module
- [ ] add deterministic store-backed request loading
- [ ] share canonical decision-row loading with evidence-head generation
- [ ] retain current CLI JSON output and exit behavior

**Verification:**
- [ ] passing pre-refactor CLI and evidence-head characterization fixtures remain byte-stable
- [ ] store request and JSON request produce equivalent solver/evaluation result
- [ ] evidence-head fingerprint remains unchanged for existing database fixture

**Exit Criteria:**
- candidate logic has one owner and two boundary adapters

### Wave 2: read-only page and navigation

**Purpose:**
- provide useful inspection before allowing mutations

**Steps:**
- [ ] add navigation link and GET route
- [ ] build one page context from policy, evidence head, and lifecycle inspection
- [ ] render empty, zero-residual, learned-active, candidate, and history states
- [ ] reuse existing CSS tokens and components

**Verification:**
- [ ] page renders with empty database
- [ ] page renders active and historical lifecycle rows without raw JSON dumps
- [ ] page has no editable optimizer parameter field

**Exit Criteria:**
- operator can understand current optimization state without terminal access

### Wave 3: optimize and lifecycle forms

**Purpose:**
- expose bounded native actions

**Steps:**
- [ ] add optimize-current-evidence POST
- [ ] add activation and rejection POSTs
- [ ] add rollback POST
- [ ] apply server-side validation, CAS tokens, notices, and PRG

**Verification:**
- [ ] each action reuses existing store or shared service owner
- [ ] stale evidence and concurrent mutations return explicit notices without partial writes
- [ ] repeated candidate submission remains idempotent

**Exit Criteria:**
- full lifecycle is usable without CLI while preserving Phase 7 guarantees

### Wave 4: runtime packaging and closeout

**Purpose:**
- ensure deployed control plane can run existing solver

**Steps:**
- [ ] install existing optional extra from `pyproject.toml` in Docker image
- [ ] document local development extra requirement
- [ ] update feature metadata and architecture/configuration docs
- [ ] run focused and live control-plane verification

**Verification:**
- [ ] Docker image reports CVXPY and CLARABEL available
- [ ] live page creates a candidate from stored ratings
- [ ] candidate remains inactive until explicit activation

**Exit Criteria:**
- page works in local Docker deployment and docs identify all SSOT owners

## Design Decisions

### Decision: one page, not a settings section

- context: optimization is an auditable operation and policy lifecycle, not a
  mutable preference setting
- choice: add dedicated `/admin/optimization` page
- alternatives considered:
  - add buttons to Settings
  - add controls to each run detail page
- impact:
  - one global domain view owns cross-run evidence and policy history

### Decision: optimize current evidence is the primary action

- context: users should not prepare JSON bundles or choose low-level commands
- choice: one button performs candidate training plus evaluation and persists the
  typed attempt
- alternatives considered:
  - separate Train and Evaluate buttons
  - JSON upload
- impact:
  - UI matches user intent while CLI retains expert/debug boundaries

### Decision: parameters remain read-only

- context: `decision_learning.yaml` is versioned SSOT and fingerprints depend on
  exact policy
- choice: show policy values/fingerprints for inspection but expose no editable
  alpha, margin, regularization, norm, solver, threshold, or iteration field
- alternatives considered:
  - Anki-style editable parameter text box
  - admin settings group
- impact:
  - no hidden policy shadow and no runtime normalization drift

### Decision: synchronous first implementation

- context: candidate creation is operator-triggered, low-volume, and bounded by
  existing solver limits
- choice: execute in one FastAPI POST and redirect after persistence
- alternatives considered:
  - new optimization job table
  - RQ job with polling
- impact:
  - no new queue state or polling UI; if measured p95 exceeds 5 seconds or HTTP
    timeouts occur, route the same shared function through existing RQ

### Decision: use existing optional dependency as packaging SSOT

- context: control-plane Docker image currently lacks CVXPY
- choice: install `.[inverse-optimization]` from `pyproject.toml`
- alternatives considered:
  - duplicate CVXPY version in requirements or Dockerfile
  - subprocess to a host environment
- impact:
  - one dependency version owner; web and worker images remain symmetric

### Decision: no new persistence tables

- context: existing tables already own training attempts, snapshots, events, and
  evidence
- choice: derive page state from existing tables
- alternatives considered:
  - UI action log table
  - optimization page cache table
- impact:
  - smaller schema and no competing history truth

## Invariants

- `config/policy/decision_learning.yaml` remains sole optimizer-policy owner.
- HTML and POST bodies cannot override optimizer numeric parameters.
- Raw 1-5-star events remain immutable source evidence.
- Effective ratings and preference edges use existing shared reducers/compiler.
- CLI and UI candidate creation call one shared orchestration function.
- UI never shells out to `scripts/run_inverse_optimization.py`.
- Candidate creation never activates policy automatically.
- Activation, rejection, and rollback remain transactional and append-only audited.
- Evidence-head, expected-parent, runtime, config, and activation-policy checks
  remain enforced at mutation time.
- Empty or insufficient evidence produces typed non-success state, not fake policy.
- Missing evaluation context remains unknown; UI never fabricates coverage.
- Existing `strong | stretch | skip` baseline labels and CV gates remain unchanged.
- Application-interest ratings remain separate from application history.
- No new BM25/BM25F behavior is introduced.
- No new database table is required for the first page.
- Core actions remain usable with native HTML forms and keyboard navigation.

## Acceptance Criteria

1. Navigation contains **Optimization** and opens `/admin/optimization`.
2. Empty database page renders `200`, explains missing ratings, and has no active
   candidate controls.
3. Page displays current evidence and policy lifecycle from existing store owners.
4. Page displays at most 50 newest effective saved ratings from the canonical typed
   request and shared event reducer, without copied evidence or mutation controls.
5. **Optimize Current Evidence** requires no file upload or JSON input.
6. Optimizing with sufficient evidence persists one training attempt and, when
   eligible, one candidate snapshot.
7. Candidate remains inactive after optimization.
8. Repeating same optimize request against unchanged evidence remains idempotent.
9. Stale evidence or changed parent produces explicit conflict/warning and no
   partial write.
10. Activation succeeds only through existing CAS/provenance checks.
11. Rejection requires actor and reason and appends existing lifecycle event.
12. Rollback restores exact target learned payload or canonical zero residual.
13. Page shows candidate metrics, reason codes, and history without raw traceback.
14. No optimizer parameter can be edited through page, URL, or POST body.
15. CLI candidate behavior and canonical JSON remain unchanged.
16. Docker control plane can import CVXPY and finds CLARABEL.
17. Rating, ranking, pipeline, and lifecycle regression suites remain green.
18. Forms have labels, fieldsets where grouped, keyboard focus, and native required
    validation.
19. Page uses redirect-after-POST and browser refresh does not repeat mutation.

## Non-Goals

- optimizer simulator
- automatic activation
- editable optimizer or activation parameters
- per-user or per-profile policy registries
- multiple optimization domains
- scheduled optimization
- background queue and polling in first implementation
- new solver, objective, compiler, or evaluation logic
- JSON training-bundle upload UI
- changing baseline ranking factors or labels
- replacing the expert CLI
- inferring application history from ratings
- copying Anki/FSRS visual or parameter semantics

## Risks and Mitigations

### Risk: solver dependency missing in deployed image

- mitigation: install the existing optional extra from `pyproject.toml` and add
  Docker smoke proof

### Risk: web request becomes slow as evidence grows

- mitigation: keep existing solver bounds, record duration, and move the same
  shared function to existing RQ only when p95 exceeds 5 seconds or timeouts occur

### Risk: UI duplicates CLI candidate logic

- mitigation: extract one shared candidate function before adding POST route

### Risk: request loader drifts from evidence-head fingerprint

- mitigation: share canonical decision-row loading; test fingerprint unchanged

### Risk: user mistakes candidate for active policy

- mitigation: separate Candidate and Active Policy cards; explicit inactive badge;
  manual activation only

### Risk: stale browser page mutates newer policy state

- mitigation: hidden evidence and parent tokens plus existing store CAS checks

### Risk: missing evaluation context looks like successful coverage

- mitigation: render `unknown` and `not available`; never synthesize evidence

## Validation Plan

- proof target: page renders all admissible empty and populated states
  - method: FastAPI TestClient tests with SQLite fixtures
  - evidence: tests covering empty DB, zero ratings, candidate, active learned,
    zero residual, rejected, stale, and history states

- proof target: UI and CLI use identical candidate operation
  - method: call both adapters with equivalent requests and compare canonical result
  - evidence: byte-equivalent result payload excluding boundary-only formatting

- proof target: store-backed request is deterministic
  - method: load same database twice and compare dataclasses/fingerprints
  - evidence: exact equality and stable event order

- proof target: existing evidence-head contract does not drift
  - method: run a passing characterization fixture before the refactor and unchanged after it
  - evidence: unchanged `decision_evidence_head_v1` fingerprint

- proof target: optimize action is idempotent and does not auto-activate
  - method: repeated POST with unchanged evidence
  - evidence: same training/snapshot identity and zero activation events

- proof target: lifecycle safety remains intact
  - method: activation, rejection, rollback, stale evidence, stale parent, concurrent
    activation, and injected transaction-failure tests
  - evidence: one winner, explicit conflicts, exact rollback, no partial writes

- proof target: page cannot shadow policy
  - method: submit unexpected numeric and policy fields
  - evidence: fields ignored or rejected; policy fingerprint unchanged

- proof target: native accessible interaction
  - method: HTML inspection and browser keyboard smoke test
  - evidence: labels, required attributes, fieldsets, focusable buttons, no JS-only action

- proof target: deployed image can solve
  - method: Docker build plus solver availability command and live candidate run
  - evidence: CVXPY import, CLARABEL listed, persisted candidate result

- proof target: documentation and feature lineage remain consistent
  - method: architecture sync check, planning lifecycle validation, repo validator
  - evidence: validator exit code 0 and generated discovery updates

## Completion Criteria

This specification is ready for implementation planning when:

1. user approves dedicated page, read-only policy, store-backed evidence, and
   synchronous first implementation
2. no unresolved owner or lifecycle boundary remains
3. route, page, store, service, packaging, and validation contracts are explicit
4. implementation plan can sequence work without inventing new semantics

Implementation is complete when:

1. every Acceptance Criterion passes
2. existing CLI, solver, ranking, rating, and policy-lifecycle tests remain green
3. Docker live run proves candidate creation and manual activation separation
4. architecture/configuration docs and feature metadata are synchronized
6. audit evidence records empty, success, insufficient, stale, conflict, activation,
   rejection, and rollback behavior

Canonical source-of-truth:

<LINK>
- `docs/superpowers/specs/2026-07-14-22-25-fitcv-inverse-optimization-master-ssot-symmetry-spec.md`
- `docs/superpowers/specs/2026-07-16-11-05-fitcv-inverse-optimization-phase-7-policy-lifecycle-runtime-residual-closeout-spec.md`
- `config/policy/decision_learning.yaml`
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
