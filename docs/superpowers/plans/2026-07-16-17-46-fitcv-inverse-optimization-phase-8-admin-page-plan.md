---
layer: change
artifact_type: plan
status: completed
completed_at: 2026-07-16T18:45:38.0472436+02:00
change_id: 2026-07-16-fitcv-inverse-optimization-phase-8-admin-page
verification:
  - 812 inverse-optimization, feedback, ranking, pipeline, store, SQLite, app, service, and page tests passed.
  - Docker web and worker images built from one Dockerfile with the inverse-optimization extra.
  - Docker web image imported CVXPY 1.9.2 and exposed CLARABEL.
  - Architecture generation/check, planning lifecycle, template, hook, repo-contract, and diff validation passed.
  - Native HTML assertions cover labels, required fields, disabled empty state, compare tokens, navigation, and redirect-after-POST.
  - Rating Evidence table derives effective ratings from the typed request and shared reducer, newest first, bounded to 50 rows.
outcome:
  summary: Completed Phase 8 shared candidate orchestration, store-backed optimization page with canonical rating evidence, manual lifecycle controls, solver-ready packaging, and synchronized SSOT documentation.
template_id: implementation-plan
name: fitcv-inverse-optimization-phase-8-admin-page-implementation
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-stage-authority-contract
parent_spec: docs/superpowers/specs/2026-07-16-17-34-fitcv-inverse-optimization-phase-8-admin-page-spec.md
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
  - docs/generated/architecture_dag.yaml
  - docs/generated/capability_lineage.yaml
  - docs/generated/planning_lineage.yaml
related_features:
  - admin_control_plane_core
  - cv_system
  - inspection_debugging
  - ui_consistency_theming
related_stages:
  - ranking
---

# FitCV inverse optimization Phase 8 admin page implementation plan

## Goal

Add one native, accessible **Preference Optimization** page that lets an operator
create and manage `ranking_v1` learned-policy candidates from current immutable
rating evidence without JSON uploads, terminal commands, editable optimizer
parameters, subprocesses, or new persistence tables.

Canonical execution path:

```text
SQLite decision evidence
-> one canonical evidence-row loader
-> ControlPlaneStore.load_inverse_optimization_request("ranking_v1")
-> create_ranking_policy_candidate(...)
-> existing solver/evaluator and immutable lifecycle tables
-> one server-side page context
-> native HTML GET/POST adapters with redirect-after-POST
```

Execution constraints:

- preserve `config/policy/decision_learning.yaml` as optimizer-policy SSOT
- preserve existing `decision_evidence_head_v1` bytes and fingerprint
- preserve current CLI candidate JSON and exit-code contract
- preserve Phase 7 activation, rejection, rollback, CAS, provenance, transaction,
  and append-only audit behavior
- keep candidate creation synchronous and inactive until explicit activation
- use functions, native forms, existing CSS tokens, SQLite, and standard-library
  adapters; add no class hierarchy, queue state, JavaScript requirement, or table
- never modify or stage unrelated Phase 7 dirty files or `.tmp-tests/`

## Key Deliverables

### Shared evidence and candidate application boundary

SQLite loads one deterministic canonical decision-row set for both evidence-head
generation and `InverseOptimizationRequest` construction. CLI and HTTP call one
`create_ranking_policy_candidate(...)` function while retaining existing solver,
evaluation, persistence, fingerprint, JSON, and exit behavior.

### Native optimization inspection page

`GET /admin/optimization` and navigation label **Optimization** render current
evidence, policy mode, latest candidate, compatible rollback targets, and existing
training/snapshot/event history. Empty, insufficient, stale, conflict, failure,
learned-active, and zero-residual states remain explicit and typed.

### Safe optimization and lifecycle forms

Native POST forms create candidates, activate, reject, and rollback through
existing owners. Server-side validation fixes domain to `ranking_v1`, rejects
policy-shadow fields, validates actor/reason/confirmation inputs, preserves
compare tokens, and redirects with bounded notice codes instead of raw errors.

### Solver-ready deployment and lifecycle documentation

Docker installs existing `.[inverse-optimization]` extra from `pyproject.toml`.
Product docs, feature sources, generated architecture/lineage surfaces, and audit
evidence describe one SSOT, symmetric CLI/UI adapters, and measured synchronous
operation without duplicating CVXPY policy.

## Task/Wave Breakdown

### Task 1: Canonicalize SQLite evidence loading

**Purpose:**
- Give evidence-head hashing and request construction one ordered SQLite row set
  without changing persisted evidence semantics or fingerprints.

**Files:**
- Inspect: `src/fitcv_cp/sqlite_store.py`
- Modify: `src/fitcv_cp/sqlite_store.py`
- Modify: `tests/test_fitcv_cp/test_sqlite_store.py`
- Verify: `tests/test_fitcv_cp/test_sqlite_store.py`

**Preconditions:**
- Record current dirty-file baseline; exclude unrelated Phase 7 files and
  `.tmp-tests/` from every patch and command.
- Run `./scripts/get_gitnexus_freshness.ps1`; refresh index before high-trust
  impact work when practical.
- Run GitNexus upstream impact on `get_decision_evidence_head`; warn before edits
  if risk is `HIGH` or `CRITICAL`.

**Steps:**
- [x] Add and run a passing pre-refactor SQLite characterization fixture freezing
  current `decision_evidence_head_v1` payload and fingerprint, including
  deterministic episode, alternative, and event ordering.
- [x] Add failing test proving one canonical loader returns identical rows on
  repeated reads and handles empty database, episodes without ratings, rating
  supersession, and missing optional evaluation context.
- [x] Extract existing ordered queries into one private canonical row-loader helper
  used by `get_decision_evidence_head`; add no cache or copied DTO.
- [x] Keep native transaction scope and `json` decoding; preserve current watermark
  and canonical serialization inputs exactly.
- [x] Delete any duplicated row-loading query introduced during change.

**Verification:**
- [x] `.venv\Scripts\python.exe -m pytest tests/test_fitcv_cp/test_sqlite_store.py -k "evidence_head or decision_evidence" -q`
- [x] Frozen pre-change and post-change evidence payloads and fingerprints match
  exactly.

**Exit Criteria:**
- One canonical SQLite loader owns ordered decision evidence; evidence-head
  contract remains byte-stable.

### Task 2: Build store-backed inverse-optimization requests

**Purpose:**
- Construct one typed `InverseOptimizationRequest` from current immutable SQLite
  evidence without inventing evaluation facts.

**Files:**
- Inspect: `src/fitcv/inverse_optimization.py`
- Modify: `src/fitcv_cp/store.py`
- Modify: `src/fitcv_cp/sqlite_store.py`
- Modify: `tests/test_fitcv_cp/test_store.py`
- Modify: `tests/test_fitcv_cp/test_sqlite_store.py`
- Verify: `tests/test_inverse_optimization.py`

**Preconditions:**
- Task 1 complete.
- Run GitNexus upstream impact on `ControlPlaneStore` and canonical SQLite loader
  before modifying their method surfaces.

**Steps:**
- [x] Add failing protocol/delegation tests for
  `ControlPlaneStore.load_inverse_optimization_request(domain_id)`.
- [x] Add failing SQLite tests for empty, zero-rating, sufficient-rating,
  superseded-rating, stable ordering, and absent evaluation-context cases.
- [x] Build existing Phase 4-6 typed episode, alternative, rating-event, and
  evaluation-context values from canonical rows; reuse existing validators and
  dataclasses instead of recreating parsing rules.
- [x] Keep domain validation explicit and fixed by caller to `ranking_v1`; reject
  unknown or malformed persisted evidence through existing typed errors.
- [x] Set `evaluation_context=None` for every Phase 8 store-loaded episode; no
  canonical persisted evaluation-context owner exists, so do not search artifacts
  or synthesize location, language, retrieval, or relevance coverage.
- [x] Prove request equality and evidence-head equality across repeated loads.

**Verification:**
- [x] `.venv\Scripts\python.exe -m pytest tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_inverse_optimization.py -k "inverse_optimization_request or evidence_head" -q`

**Exit Criteria:**
- Store API returns one deterministic typed request using same evidence rows and
  ordering as evidence-head generation.

### Task 3: Extract shared candidate orchestration

**Purpose:**
- Make CLI and HTTP thin symmetric adapters over one candidate operation.

**Files:**
- Inspect: `scripts/run_inverse_optimization.py`
- Inspect: `src/fitcv/inverse_optimization.py`
- Create: `src/fitcv_cp/optimization_service.py`
- Modify: `scripts/run_inverse_optimization.py`
- Modify: `tests/test_inverse_optimization.py`
- Create: `tests/test_fitcv_cp/test_optimization_service.py`
- Modify: `tests/test_fitcv_cp/test_store.py`
- Verify: `config/policy/decision_learning.yaml`

**Preconditions:**
- Task 2 complete.
- Run GitNexus upstream impact on `_candidate_operation`,
  `persist_candidate_attempt`, and lifecycle store calls; warn before edits for
  `HIGH` or `CRITICAL` risk.

**Steps:**
- [x] Add and run passing pre-refactor CLI `candidate` characterization tests for
  canonical JSON, status, persistence rows, no-op behavior, idempotency, and exit code.
- [x] Add failing service tests for sufficient evidence, insufficient evidence,
  solver failure, evaluation rejection, unchanged evidence, stale evidence,
  changed parent, and unchanged repeated request.
- [x] Create one metadata-compliant function module containing
  `create_ranking_policy_candidate(request, *, store, config, expected_evidence_head_fingerprint=None, expected_parent_ref=None)` and only small
  private helpers required by moved orchestration.
- [x] Move policy validation, evidence/parent/provenance checks, solve/evaluate,
  immutable row construction, atomic persistence, and typed result assembly from
  CLI into shared function without moving solver math or SQL.
- [x] Keep JSON parsing, output-path writes, canonical serialization, and exit
  mapping in CLI; replace `_candidate_operation` ownership with direct shared
  function use or boundary-only compatibility wrapper.
- [x] Inject `ControlPlaneStore` and loaded config explicitly; create no service
  class, global mutable store, subprocess, or new command framework.
- [x] Pass expected evidence-head and parent tokens into shared function; reject
  mismatches before solving and recheck before persistence.
- [x] Compare CLI-bundle and store-loaded requests through shared function and
  assert equivalent canonical result excluding boundary-only formatting.

**Verification:**
- [x] `.venv\Scripts\python.exe -m pytest tests/test_inverse_optimization.py tests/test_fitcv_cp/test_optimization_service.py tests/test_fitcv_cp/test_store.py -q`
- [x] Existing CLI golden payload remains byte-equivalent.
- [x] Web-facing module imports no FastAPI template or subprocess dependency.

**Exit Criteria:**
- Candidate orchestration has one owner; CLI and future page differ only at input
  and output boundaries.

### Task 4: Add read-only optimization page

**Purpose:**
- Let operators inspect current optimization evidence and lifecycle before any
  mutation is exposed.

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/base.html`
- Create: `src/fitcv_cp/templates/optimization.html`
- Create: `tests/test_fitcv_cp/test_optimization_page.py`
- Verify: `tests/test_fitcv_cp/test_app.py`
- Verify: `src/fitcv_cp/sqlite_store.py`

**Preconditions:**
- Tasks 1-3 complete.
- Run GitNexus upstream impact on selected page-context helpers and route-adjacent
  symbols before edits.

**Steps:**
- [x] Add failing TestClient cases for navigation, empty database, zero ratings,
  active zero residual, active learned policy, latest candidate, rejected/stale
  candidate, compatible rollback targets, and newest-first history limited to 25.
- [x] Add one GET route for `/admin/optimization` using existing store resolution,
  template rendering, error handling, and request-context patterns.
- [x] Extend lifecycle inspection with optional SQL-level `limit` and descending
  order; UI requests 25 rows while CLI retains unbounded behavior.
- [x] Build one server-side view model from evidence head, current typed request
  counts when available, lifecycle inspection, config fingerprints, active policy,
  latest candidate, and store-projected rollback eligibility.
- [x] Derive a read-only Rating Evidence projection from the typed request and
  shared rating-event reducer; show only effective ratings, newest first, limited
  to 50 rows, without a copied ledger or mutation controls.
- [x] Add one status/reason-code mapper in Python for badge class and bounded human
  text; template must not duplicate lifecycle vocabulary branches.
- [x] Add **Optimization** navigation link in `base.html` and render page titled
  **Preference Optimization** with existing cards, badges, tables, buttons, and
  responsive CSS tokens.
- [x] Render fingerprints in `<code>` with full values available to assistive or
  inspection text; render missing evaluation context as `unknown` or
  `not available`.
- [x] Show no editable alpha, margin, regularization, norm, solver, threshold,
  iteration, or policy field; use no JavaScript for core page behavior.

**Verification:**
- [x] `.venv\Scripts\python.exe -m pytest tests/test_fitcv_cp/test_optimization_page.py -q`
- [x] HTML assertions prove `200`, navigation, section headings, typed empty state,
  three history tables, canonical Rating Evidence content and links, no raw
  traceback, and no optimizer input names.

**Exit Criteria:**
- Operator can inspect all admissible current states without CLI access or hidden
  shadow policy.

### Task 5: Add optimize-current-evidence action

**Purpose:**
- Create an inactive candidate from current stored ratings through one native form
  and shared operation.

**Files:**
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/optimization.html`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Verify: `src/fitcv_cp/optimization_service.py`
- Verify: `src/fitcv_cp/store.py`

**Preconditions:**
- Task 4 complete.
- Run GitNexus upstream impact on new route-adjacent helper symbols before edits.

**Steps:**
- [x] Add failing TestClient tests for disabled empty-evidence form, server-side
  empty bypass, sufficient evidence, insufficient evidence, solver unavailable,
  repeated submission, stale evidence, changed parent, and persistence failure.
- [x] Render hidden canonical domain, evidence-head token, expected-parent token,
  helper text, and **Optimize Current Evidence** submit button. Candidate creation
  has no actor field.
- [x] Add `POST /admin/optimization/candidate`; validate fixed `ranking_v1`,
  accept only declared native form fields, reload request through store, and invoke
  shared candidate function with submitted compare tokens.
- [x] Map typed result status/reason codes to bounded notice codes and issue `303`
  redirect; never place raw exception text or payload JSON in query strings.
- [x] Preserve idempotent persisted identities and prove candidate creation adds no
  activation event and does not change active policy.
- [x] Record operation duration through existing logging/observability path only;
  add no queue until measured p95 exceeds five seconds or timeouts occur.

**Verification:**
- [x] `.venv\Scripts\python.exe -m pytest tests/test_fitcv_cp/test_optimization_page.py tests/test_fitcv_cp/test_optimization_service.py tests/test_inverse_optimization.py -q`
- [x] Repeated identical POST yields same training/snapshot identity and zero
  activation events.

**Exit Criteria:**
- Current immutable evidence creates one typed inactive candidate through PRG with
  no file upload, JSON input, or policy override.

### Task 6: Add manual lifecycle actions

**Purpose:**
- Expose activation, rejection, and rollback without weakening Phase 7 lifecycle
  contracts.

**Files:**
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/optimization.html`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_sqlite_store.py`
- Verify: `src/fitcv_cp/store.py`

**Preconditions:**
- Task 5 complete.
- Run GitNexus upstream impact on `activate_ranking_policy_candidate`,
  `reject_ranking_policy_candidate`, and `rollback_ranking_policy`; warn before
  edits for `HIGH` or `CRITICAL` risk.

**Steps:**
- [x] Add failing HTTP tests for eligible activation, stale evidence, stale parent,
  concurrent activation, invalid state, rejection validation, conflicting
  rejection, learned rollback, zero-residual rollback, incompatible target,
  changed active snapshot, missing confirmation, and injected transaction failure.
- [x] Render activation and rejection forms only for eligible candidate state;
  include snapshot ID and current compare tokens while retaining server authority.
- [x] Require normalized actor and bounded non-empty rejection reason; call existing
  store rejection operation unchanged.
- [x] Render rollback `<select>` from prior learned snapshots marked eligible by
  store inspection plus `zero_residual`; require native confirmation checkbox,
  expected-active token, and actor.
- [x] Add activation, rejection, and rollback POST routes from spec; call existing
  store methods, translate existing typed outcomes, and redirect `303`.
- [x] Ignore UI visibility as authorization; enforce all current evidence,
  provenance, parent, active-reference, config, runtime, and transaction checks at
  mutation time.
- [x] Prove each successful action appends existing lifecycle event and each failed
  action leaves training, snapshot, active state, and event ledger atomic.

**Verification:**
- [x] `.venv\Scripts\python.exe -m pytest tests/test_fitcv_cp/test_optimization_page.py tests/test_fitcv_cp/test_sqlite_store.py -q`
- [x] Existing two-thread activation, injected-failure, and exact-rollback tests
  remain green.

**Exit Criteria:**
- Full manual lifecycle works through native forms while retaining existing CAS,
  provenance, immutability, and append-only audit guarantees.

### Task 7: Install existing solver extra in Docker

**Purpose:**
- Make web and worker images execute shared solver without adding a second
  dependency owner.

**Files:**
- Inspect: `pyproject.toml`
- Inspect: `requirements.txt`
- Modify: `Dockerfile`
- Verify: `docker-compose.yml`

**Preconditions:**
- Tasks 1-6 complete.
- Existing `inverse-optimization` extra remains defined in `pyproject.toml`.

**Steps:**
- [x] Replace editable Docker install exactly with
  `RUN pip install -e ".[inverse-optimization]"`; remove `--no-deps`.
- [x] Add no CVXPY or CLARABEL version to `requirements.txt`, Dockerfile, app
  config, or HTML.
- [x] Build same Dockerfile for `web` and `worker`; add no optimization-only image.
- [x] Smoke import `cvxpy`, assert `CLARABEL` appears in installed solvers, and run
  one bounded candidate operation inside image.

**Verification:**
- [x] `docker compose build web worker`
- [x] `docker compose run --rm web python -c "import cvxpy as cp; assert 'CLARABEL' in cp.installed_solvers()"`

**Exit Criteria:**
- Existing optional dependency is sole solver-version owner and both control-plane
  images can solve.

### Task 8: Synchronize product docs and feature lineage

**Purpose:**
- Document page ownership, UI/CLI symmetry, packaging, lifecycle boundaries, and
  feature evidence from human-owned sources.

**Files:**
- Modify: `docs/architecture.md`
- Modify: `docs/configuration.md`
- Modify: `docs/usage.md`
- Modify: `docs/features/admin_control_plane_core/feature.source.yaml`
- Modify: `docs/features/cv_system/feature.source.yaml`
- Modify: `docs/features/inspection_debugging/feature.source.yaml`
- Modify: `docs/features/ui_consistency_theming/feature.source.yaml`
- Generate: `docs/features/*/*.yaml`
- Generate: `docs/features/*/history.md`
- Generate: `docs/features/*/lineage.generated.yaml`
- Generate: `docs/generated/architecture_dag.yaml`
- Generate: `docs/generated/capability_lineage.yaml`
- Generate: `docs/generated/planning_lineage.yaml`

**Preconditions:**
- Tasks 1-7 complete.
- Source code and tests contain required architecture metadata for new module,
  route, template, and capability proof.

**Steps:**
- [x] Document `optimization_service.py` as shared application owner, store request
  loader as evidence adapter, app routes as HTTP boundary, and existing tables as
  sole lifecycle truth.
- [x] Document `/admin/optimization`, native form workflow, read-only policy,
  synchronous v1 threshold, local solver-extra installation, and Docker behavior.
- [x] Update affected feature source capabilities/refs only; do not hand-edit
  generated feature contracts, histories, lineage, or discovery files.
- [x] Run architecture sync to generate feature, history, lineage, and discovery
  surfaces; review diff for private/public boundary compliance.
- [x] Regenerate planning lineage after plan or spec metadata changes.

**Verification:**
- [x] `.venv\Scripts\python.exe scripts/sync_architecture_docs.py`
- [x] `.venv\Scripts\python.exe scripts/sync_architecture_docs.py --check`
- [x] `.venv\Scripts\python.exe scripts/generate_planning_lineage.py`
- [x] `.venv\Scripts\python.exe scripts/validate_planning_lifecycle.py`

**Exit Criteria:**
- Human-owned docs name one owner per fact and all generated feature/discovery
  outputs derive cleanly from sources.

### Task 9: Run regression, live, and audit closeout

**Purpose:**
- Prove all spec states in source tests and deployed control-plane behavior before
  Phase 8 completion is claimed.

**Files:**
- Verify: `tests/test_inverse_optimization.py`
- Verify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_store.py`
- Verify: `tests/test_fitcv_cp/test_sqlite_store.py`
- Verify: `tests/test_decision_feedback.py`
- Verify: `tests/test_ranking.py`
- Verify: `tests/test_pipeline.py`
- Create: `docs/superpowers/plans/audit/<phase8-run-id>/`
- Modify after proof: `docs/superpowers/plans/2026-07-16-17-46-fitcv-inverse-optimization-phase-8-admin-page-plan.md`

**Preconditions:**
- Tasks 1-8 complete.
- Docker image builds with solver extra.
- Test data uses isolated temporary SQLite database; no user database reset or
  destructive cleanup occurs.

**Steps:**
- [x] Run focused store, service, CLI, page, lifecycle, accessibility, and Docker
  tests first; fix only Phase 8 regressions.
- [x] Run decision-feedback, inverse-optimization, ranking, pipeline, and
  control-plane regression suites.
- [x] Start isolated Docker control plane; verify keyboard-accessible page states
  for empty DB, insufficient evidence, successful candidate, stale/conflict,
  activation, rejection, learned rollback, and zero-residual rollback.
- [x] Verify candidate remains inactive after optimization and browser refresh
  repeats no mutation.
- [x] Capture request/result IDs, evidence fingerprints, lifecycle rows, screenshots
  or HTML assertions, Docker solver proof, commands, and exit codes in standard
  audit bundle without secrets or raw private job text.
- [x] Measure candidate POST duration; retain synchronous path unless observed p95
  exceeds five seconds or HTTP timeout evidence exists.
- [x] Run GitNexus `detect_changes` for all uncommitted changes and reconcile any
  unexpected symbols/processes source-first.
- [x] Run repository validators and `git diff --check`; mark plan completed only
  with fresh terminal metadata and evidence summary.

**Verification:**
- [x] `.venv\Scripts\python.exe -m pytest tests/test_inverse_optimization.py tests/test_decision_feedback.py tests/test_ranking.py tests/test_pipeline.py tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_app.py -q`
- [x] `.venv\Scripts\python.exe scripts/validate_template_required_sections.py`
- [x] `.venv\Scripts\python.exe scripts/validate_planning_lifecycle.py`
- [x] `.venv\Scripts\python.exe scripts/hooks/run_validator.py --fast`
- [x] `.venv\Scripts\python.exe scripts/validate_repo_contracts.py --fast`
- [x] `git diff --check`

**Exit Criteria:**
- Audit evidence covers every required state, all focused/regression/contract checks
  pass, affected scope matches plan, and no unrelated dirty file is changed.

## Verification

Final artifact-level proof:

```powershell
.venv\Scripts\python.exe -m pytest `
  tests/test_inverse_optimization.py `
  tests/test_decision_feedback.py `
  tests/test_ranking.py `
  tests/test_pipeline.py `
  tests/test_fitcv_cp/test_store.py `
  tests/test_fitcv_cp/test_sqlite_store.py `
  tests/test_fitcv_cp/test_app.py -q

docker compose build web worker
docker compose run --rm web python -c "import cvxpy as cp; assert 'CLARABEL' in cp.installed_solvers()"

.venv\Scripts\python.exe scripts/sync_architecture_docs.py --check
.venv\Scripts\python.exe scripts/validate_template_required_sections.py
.venv\Scripts\python.exe scripts/validate_planning_lifecycle.py
.venv\Scripts\python.exe scripts/hooks/run_validator.py --fast
.venv\Scripts\python.exe scripts/validate_repo_contracts.py --fast
git diff --check
```

Required evidence:

- unchanged `decision_evidence_head_v1` fixture and fingerprint
- equivalent CLI and UI shared candidate result
- idempotent candidate creation with zero automatic activation events
- explicit empty, insufficient, stale, conflict, failure, candidate, learned-active,
  rejected, and zero-residual page states
- exact activation, rejection, learned rollback, and zero-residual rollback behavior
- no editable optimizer policy field and no web subprocess path
- native labels, required inputs, fieldsets, confirmation, keyboard focus, and PRG
- CVXPY import and CLARABEL availability in same Docker image used by web/worker
- generated docs/lineage synchronized from source files
- GitNexus changed-scope report limited to expected evidence, service, CLI, HTTP,
  template, packaging, tests, and docs flows

## Completion Criteria

Phase 8 plan is complete when:

1. all Key Deliverables are implemented and verified
2. Tasks 1-9 are complete or explicitly dropped with reason
3. canonical SQLite evidence loading has one owner
4. evidence-head payload and fingerprint remain unchanged
5. store-backed request loading is deterministic across every admissible evidence state
6. CLI and UI call one shared candidate function
7. CLI candidate canonical JSON and exit behavior remain unchanged
8. `/admin/optimization` renders every required current and historical state
9. optimization needs no JSON upload and never auto-activates
10. activation, rejection, and rollback retain Phase 7 transactional/CAS guarantees
11. no HTML, URL, or POST field can shadow optimizer policy
12. missing evaluation context remains visibly unknown or unavailable
13. Docker web and worker images install existing optional extra and expose CLARABEL
14. native accessibility and redirect-after-POST behavior are verified
15. source docs and generated feature/architecture/planning lineage are synchronized
16. audit evidence covers empty, success, insufficient, stale, conflict, failure,
    activation, rejection, and rollback cases
17. focused and regression suites pass
18. GitNexus changed-scope report matches intended surfaces
19. unrelated Phase 7 dirty files and `.tmp-tests/` remain untouched
20. plan has terminal metadata and fresh verification evidence before closure

Canonical source-of-truth:

<LINK>
- `docs/superpowers/specs/2026-07-16-17-34-fitcv-inverse-optimization-phase-8-admin-page-spec.md`
- `docs/superpowers/specs/2026-07-14-22-25-fitcv-inverse-optimization-master-ssot-symmetry-spec.md`
- `docs/superpowers/specs/2026-07-16-11-05-fitcv-inverse-optimization-phase-7-policy-lifecycle-runtime-residual-closeout-spec.md`
- `config/policy/decision_learning.yaml`
- `src/fitcv/inverse_optimization.py`
- `src/fitcv_cp/store.py`
- `src/fitcv_cp/sqlite_store.py`
- `scripts/run_inverse_optimization.py`
- `docs/operating_system/governance/repo-governance.md`
- `docs/operating_system/lifecycle/doc-system-lifecycle.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>


## Closeout Notes

- Local mypy command was unavailable because mypy is not installed in the project virtual environment; enforced Python metadata and repo-contract validators passed.
- Browser interaction proof uses native HTML/TestClient assertions; no JavaScript is required for optimization actions.
- GitNexus whole-worktree scope reported CRITICAL because the branch already contains broad Phase 7 changes; Phase 8 pre-edit symbol impacts were LOW.
