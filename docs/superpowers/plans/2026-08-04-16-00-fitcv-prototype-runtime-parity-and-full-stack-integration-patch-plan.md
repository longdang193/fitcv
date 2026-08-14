---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: fitcv-prototype-runtime-parity-and-full-stack-integration-patch
parent_spec: none
coordination:
  target_branch: main
  base_ref: 488914851a072a362187f7c785665e4b05bb5b65
  mode: inline_sequential
  tasks:
    - id: task-1-shared-shell-and-lifecycle-removal
      depends_on: []
      execution_mode: inline_sequential
      allowed_paths:
        - docs/fitcv-settings-ui-prototype.integration.md
        - docs/superpowers/plans/2026-08-04-16-00-fitcv-prototype-runtime-parity-and-full-stack-integration-patch-plan.md
        - src/fitcv_cp/app.py
        - src/fitcv_cp/local_routes.py
        - src/fitcv_cp/templates/base.html
        - src/fitcv_cp/templates/lifecycle.html
        - tests/test_fitcv_cp/test_app.py
        - tests/test_fitcv_cp/test_lifecycle_removal.py
        - tests/test_fitcv_cp/test_local_routes.py
      planned_write_paths:
        - docs/fitcv-settings-ui-prototype.integration.md
        - docs/superpowers/plans/2026-08-04-16-00-fitcv-prototype-runtime-parity-and-full-stack-integration-patch-plan.md
        - src/fitcv_cp/app.py
        - src/fitcv_cp/local_routes.py
        - src/fitcv_cp/templates/base.html
        - src/fitcv_cp/templates/lifecycle.html
        - tests/test_fitcv_cp/test_app.py
        - tests/test_fitcv_cp/test_lifecycle_removal.py
        - tests/test_fitcv_cp/test_local_routes.py
    - id: task-2-pipeline-settings
      depends_on: [task-1-shared-shell-and-lifecycle-removal]
      execution_mode: inline_sequential
      allowed_paths: [docs/fitcv-settings-ui-prototype.integration.md, docs/superpowers/plans/2026-08-04-16-00-fitcv-prototype-runtime-parity-and-full-stack-integration-patch-plan.md, src/fitcv_cp/settings_schema.py, src/fitcv_cp/templates/settings.html, tests/test_fitcv_cp/test_app.py, tests/test_fitcv_cp/test_local_routes.py, tests/test_fitcv_cp/test_settings_schema.py]
      planned_write_paths: [docs/fitcv-settings-ui-prototype.integration.md, docs/superpowers/plans/2026-08-04-16-00-fitcv-prototype-runtime-parity-and-full-stack-integration-patch-plan.md, src/fitcv_cp/settings_schema.py, src/fitcv_cp/templates/settings.html, tests/test_fitcv_cp/test_app.py, tests/test_fitcv_cp/test_local_routes.py, tests/test_fitcv_cp/test_settings_schema.py]
    - id: task-3-api-providers
      depends_on: [task-2-pipeline-settings]
      execution_mode: inline_sequential
      allowed_paths: [docs/fitcv-settings-ui-prototype.integration.md, docs/superpowers/plans/2026-08-04-16-00-fitcv-prototype-runtime-parity-and-full-stack-integration-patch-plan.md, src/fitcv_cp/templates/api_provider_detail.html, src/fitcv_cp/templates/api_providers.html, tests/test_fitcv_cp/test_app.py, tests/test_fitcv_cp/test_local_app.py, tests/test_fitcv_cp/test_local_routes.py]
      planned_write_paths: [docs/fitcv-settings-ui-prototype.integration.md, docs/superpowers/plans/2026-08-04-16-00-fitcv-prototype-runtime-parity-and-full-stack-integration-patch-plan.md, src/fitcv_cp/templates/api_provider_detail.html, src/fitcv_cp/templates/api_providers.html, tests/test_fitcv_cp/test_app.py, tests/test_fitcv_cp/test_local_app.py, tests/test_fitcv_cp/test_local_routes.py]
    - id: task-4-llm-configuration
      depends_on: [task-3-api-providers]
      execution_mode: inline_sequential
      allowed_paths: [docs/fitcv-settings-ui-prototype.integration.md, docs/superpowers/plans/2026-08-04-16-00-fitcv-prototype-runtime-parity-and-full-stack-integration-patch-plan.md, src/fitcv_cp/templates/llm_configuration.html, tests/test_fitcv_cp/test_app.py, tests/test_fitcv_cp/test_local_app.py, tests/test_fitcv_cp/test_local_routes.py]
      planned_write_paths: [docs/fitcv-settings-ui-prototype.integration.md, docs/superpowers/plans/2026-08-04-16-00-fitcv-prototype-runtime-parity-and-full-stack-integration-patch-plan.md, src/fitcv_cp/templates/llm_configuration.html, tests/test_fitcv_cp/test_app.py, tests/test_fitcv_cp/test_local_app.py, tests/test_fitcv_cp/test_local_routes.py]
    - id: task-5-prompt-management
      depends_on: [task-4-llm-configuration]
      execution_mode: inline_sequential
      allowed_paths: [docs/fitcv-settings-ui-prototype.integration.md, docs/superpowers/plans/2026-08-04-16-00-fitcv-prototype-runtime-parity-and-full-stack-integration-patch-plan.md, src/fitcv_cp/templates/prompt_management.html, tests/test_fitcv_cp/test_app.py, tests/test_fitcv_cp/test_local_app.py, tests/test_fitcv_cp/test_local_routes.py]
      planned_write_paths: [docs/fitcv-settings-ui-prototype.integration.md, docs/superpowers/plans/2026-08-04-16-00-fitcv-prototype-runtime-parity-and-full-stack-integration-patch-plan.md, src/fitcv_cp/templates/prompt_management.html, tests/test_fitcv_cp/test_app.py, tests/test_fitcv_cp/test_local_app.py, tests/test_fitcv_cp/test_local_routes.py]
    - id: task-6-system-and-data-backup
      depends_on: [task-5-prompt-management]
      execution_mode: inline_sequential
      allowed_paths: [docs/fitcv-settings-ui-prototype.integration.md, docs/superpowers/plans/2026-08-04-16-00-fitcv-prototype-runtime-parity-and-full-stack-integration-patch-plan.md, src/fitcv_cp/templates/_data_backup_panel.html, src/fitcv_cp/templates/local_data_backup.html, src/fitcv_cp/templates/system.html, tests/test_fitcv_cp/test_app.py, tests/test_fitcv_cp/test_local_app.py, tests/test_fitcv_cp/test_local_routes.py]
      planned_write_paths: [docs/fitcv-settings-ui-prototype.integration.md, docs/superpowers/plans/2026-08-04-16-00-fitcv-prototype-runtime-parity-and-full-stack-integration-patch-plan.md, src/fitcv_cp/templates/_data_backup_panel.html, src/fitcv_cp/templates/local_data_backup.html, src/fitcv_cp/templates/system.html, tests/test_fitcv_cp/test_app.py, tests/test_fitcv_cp/test_local_app.py, tests/test_fitcv_cp/test_local_routes.py]
    - id: task-7-runs-list-and-trigger
      depends_on: [task-6-system-and-data-backup]
      execution_mode: inline_sequential
      allowed_paths: [docs/api.md, docs/fitcv-settings-ui-prototype.integration.md, docs/superpowers/plans/2026-08-04-16-00-fitcv-prototype-runtime-parity-and-full-stack-integration-patch-plan.md, src/fitcv_cp/app.py, src/fitcv_cp/templates/runs_list.html, tests/test_fitcv_cp/test_app.py]
      planned_write_paths: [docs/api.md, docs/fitcv-settings-ui-prototype.integration.md, docs/superpowers/plans/2026-08-04-16-00-fitcv-prototype-runtime-parity-and-full-stack-integration-patch-plan.md, src/fitcv_cp/app.py, src/fitcv_cp/templates/runs_list.html, tests/test_fitcv_cp/test_app.py]
    - id: task-8-run-details-and-results
      depends_on: [task-7-runs-list-and-trigger]
      execution_mode: inline_sequential
      allowed_paths: [docs/fitcv-settings-ui-prototype.integration.md, docs/superpowers/plans/2026-08-04-16-00-fitcv-prototype-runtime-parity-and-full-stack-integration-patch-plan.md, src/fitcv_cp/templates/_cv_review_queue.html, src/fitcv_cp/templates/_jobs_input_sources.html, src/fitcv_cp/templates/_process_console.html, src/fitcv_cp/templates/_run_detail_snapshot_tab.html, src/fitcv_cp/templates/run_detail.html, src/fitcv_cp/templates/run_detail_tab_enriched.html, src/fitcv_cp/templates/run_detail_tab_jobs_input.html, src/fitcv_cp/templates/run_detail_tab_profile.html, tests/test_fitcv_cp/test_app.py]
      planned_write_paths: [docs/fitcv-settings-ui-prototype.integration.md, docs/superpowers/plans/2026-08-04-16-00-fitcv-prototype-runtime-parity-and-full-stack-integration-patch-plan.md, src/fitcv_cp/templates/_cv_review_queue.html, src/fitcv_cp/templates/_jobs_input_sources.html, src/fitcv_cp/templates/_process_console.html, src/fitcv_cp/templates/_run_detail_snapshot_tab.html, src/fitcv_cp/templates/run_detail.html, src/fitcv_cp/templates/run_detail_tab_enriched.html, src/fitcv_cp/templates/run_detail_tab_jobs_input.html, src/fitcv_cp/templates/run_detail_tab_profile.html, tests/test_fitcv_cp/test_app.py]
    - id: task-9-scans
      depends_on: [task-8-run-details-and-results]
      execution_mode: inline_sequential
      allowed_paths: [docs/fitcv-settings-ui-prototype.integration.md, docs/superpowers/plans/2026-08-04-16-00-fitcv-prototype-runtime-parity-and-full-stack-integration-patch-plan.md, src/fitcv_cp/templates/scan_detail.html, src/fitcv_cp/templates/scans_list.html, tests/test_fitcv_cp/test_app.py, tests/test_fitcv_cp/test_scan_contracts.py, tests/test_fitcv_cp/test_scan_worker.py]
      planned_write_paths: [docs/fitcv-settings-ui-prototype.integration.md, docs/superpowers/plans/2026-08-04-16-00-fitcv-prototype-runtime-parity-and-full-stack-integration-patch-plan.md, src/fitcv_cp/templates/scan_detail.html, src/fitcv_cp/templates/scans_list.html, tests/test_fitcv_cp/test_app.py, tests/test_fitcv_cp/test_scan_contracts.py, tests/test_fitcv_cp/test_scan_worker.py]
    - id: task-10-candidate-profile-recovery
      depends_on: [task-9-scans]
      execution_mode: inline_sequential
      allowed_paths: [docs/fitcv-settings-ui-prototype.integration.md, docs/superpowers/plans/2026-08-04-16-00-fitcv-prototype-runtime-parity-and-full-stack-integration-patch-plan.md, src/fitcv_cp/templates/candidate_profile_creation.html, src/fitcv_cp/templates/candidate_profile_detail.html, src/fitcv_cp/templates/candidate_profile_sections.html, src/fitcv_cp/templates/candidate_profiles.html, tests/test_candidate_profile_template_contract.py, tests/test_fitcv_cp/test_app.py, tests/test_fitcv_cp/test_candidate_profile_service.py]
      planned_write_paths: [docs/fitcv-settings-ui-prototype.integration.md, docs/superpowers/plans/2026-08-04-16-00-fitcv-prototype-runtime-parity-and-full-stack-integration-patch-plan.md, src/fitcv_cp/templates/candidate_profile_creation.html, src/fitcv_cp/templates/candidate_profile_detail.html, src/fitcv_cp/templates/candidate_profile_sections.html, src/fitcv_cp/templates/candidate_profiles.html, tests/test_candidate_profile_template_contract.py, tests/test_fitcv_cp/test_app.py, tests/test_fitcv_cp/test_candidate_profile_service.py]
    - id: task-11-bookmarks
      depends_on: [task-10-candidate-profile-recovery]
      execution_mode: inline_sequential
      allowed_paths: [docs/fitcv-settings-ui-prototype.integration.md, docs/superpowers/plans/2026-08-04-16-00-fitcv-prototype-runtime-parity-and-full-stack-integration-patch-plan.md, src/fitcv_cp/templates/bookmarks.html, tests/test_fitcv_cp/test_app.py, tests/test_fitcv_cp/test_sqlite_store.py, tests/test_fitcv_cp/test_store.py]
      planned_write_paths: [docs/fitcv-settings-ui-prototype.integration.md, docs/superpowers/plans/2026-08-04-16-00-fitcv-prototype-runtime-parity-and-full-stack-integration-patch-plan.md, src/fitcv_cp/templates/bookmarks.html, tests/test_fitcv_cp/test_app.py, tests/test_fitcv_cp/test_sqlite_store.py, tests/test_fitcv_cp/test_store.py]
    - id: task-12-synonyms
      depends_on: [task-11-bookmarks]
      execution_mode: inline_sequential
      allowed_paths: [docs/fitcv-settings-ui-prototype.integration.md, docs/superpowers/plans/2026-08-04-16-00-fitcv-prototype-runtime-parity-and-full-stack-integration-patch-plan.md, src/fitcv_cp/templates/synonyms.html, tests/test_fitcv_cp/test_app.py, tests/test_fitcv_cp/test_synonym_global_policy_io.py, tests/test_fitcv_cp/test_synonym_promote_commit_field_aware.py, tests/test_fitcv_cp/test_synonym_promote_preview_field_aware.py]
      planned_write_paths: [docs/fitcv-settings-ui-prototype.integration.md, docs/superpowers/plans/2026-08-04-16-00-fitcv-prototype-runtime-parity-and-full-stack-integration-patch-plan.md, src/fitcv_cp/templates/synonyms.html, tests/test_fitcv_cp/test_app.py, tests/test_fitcv_cp/test_synonym_global_policy_io.py, tests/test_fitcv_cp/test_synonym_promote_commit_field_aware.py, tests/test_fitcv_cp/test_synonym_promote_preview_field_aware.py]
    - id: task-13-preference-optimization
      depends_on: [task-12-synonyms]
      execution_mode: inline_sequential
      allowed_paths: [docs/fitcv-settings-ui-prototype.integration.md, docs/superpowers/plans/2026-08-04-16-00-fitcv-prototype-runtime-parity-and-full-stack-integration-patch-plan.md, src/fitcv_cp/templates/optimization.html, tests/test_fitcv_cp/test_app.py, tests/test_fitcv_cp/test_optimization_page.py, tests/test_fitcv_cp/test_sqlite_store.py, tests/test_inverse_optimization.py]
      planned_write_paths: [docs/fitcv-settings-ui-prototype.integration.md, docs/superpowers/plans/2026-08-04-16-00-fitcv-prototype-runtime-parity-and-full-stack-integration-patch-plan.md, src/fitcv_cp/templates/optimization.html, tests/test_fitcv_cp/test_app.py, tests/test_fitcv_cp/test_optimization_page.py, tests/test_fitcv_cp/test_sqlite_store.py, tests/test_inverse_optimization.py]
targets:
  - docs/fitcv-settings-ui-prototype.html
  - docs/fitcv-settings-ui-prototype.integration.md
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates
  - tests/test_fitcv_cp
---

# FitCV Prototype Runtime Parity And Full-Stack Integration Patch Plan

## Goal

Eliminate runtime frontend drift from frozen approved prototype blob
`989af611bd7767c148022c79ac00c5069d8a3956`, then finish each affected page's
integration with current FastAPI contracts without deriving transport payloads
from prototype markup.

Prototype owns visual hierarchy, navigation, labels, actions, interaction,
default expanded state, responsive behavior, and visible UI states. FastAPI
Pydantic models, registered routes, `/openapi.json`, route tests, persistence
tests, and `docs/api.md` own transport behavior. Current uncommitted work is
preserved. Execution must not run `git clean`, `git reset --hard`, broad
formatting, stash deletion, or unrelated file edits. Port `8765` is prohibited.

## Authority And Approved Decisions

- Frozen prototype blob `989af611bd7767c148022c79ac00c5069d8a3956`
  owns visual, navigation, interaction, and visible UI-state truth only.
- Direct approved scope removes user-facing `Lifecycle`: remove
  `/admin/lifecycle` page route and `lifecycle.html`; redirect `/local/system`
  to `/admin/system`; preserve `/local/lifecycle/status` only for shutdown
  safety. Do not add a replacement sidebar item.
- FastAPI models, `/openapi.json`, registered routes, route/service/store tests,
  and `docs/api.md` own transport truth. Linked specifications are references,
  not parent authority where they conflict with this approved scope.
- `src/fitcv_cp/templates/base.html` owns shared CSS only. Page-specific CSS may
  stay with its owning template when it is not duplicated shared styling.
- Prompt Management is not confirmed parity-aligned. Audit found structural,
  copy, grouping, row-component, and dialog drift, so it receives its own slice.

## Critical Findings Governing Execution

1. Runtime Jinja templates independently restate prototype presentation. Shared
   CSS, shell hierarchy, and async-state behavior lack one runtime owner.
2. `src/fitcv_cp/templates/base.html` already owns shared shell, shared CSS, icons,
   `fitcvApiRequest`, and every page inheritance path. It is minimum shared
   owner; no frontend framework, CSS build step, client generator, or second
   component registry is needed.
3. Frozen prototype includes `Prompt Management` under Pipeline and excludes
   `Lifecycle`. Runtime must keep Prompt Management visible, remove the
   Lifecycle page, redirect `/local/system` to `/admin/system`, and preserve
   only `/local/lifecycle/status` for shutdown-dialog safety.
4. Existing API helper retains HTTP status, canonical error code, and payload,
   but pages usually render only `error.message`. Shared
   pending/error/retry/stale rendering belongs in `base.html`.
5. Candidate Profile approved markup already has dedicated parity coverage.
   That slice must reuse confirmed components and add only missing real-backend
   recovery behavior. It must not rebuild approved baseline, derived,
   confirmation, or detail structures.
6. Browser evidence proves UI behavior only. Every slice consuming or changing
   backend behavior requires direct boundary proof before browser acceptance.

## Implementation Outcomes

### One Runtime Presentation Owner

`src/fitcv_cp/templates/base.html` owns shared shell CSS, navigation/header
hierarchy, shared controls, dialogs, notices, skeletons, empty states, pending
states, canonical errors, retry actions, and stale-state recovery. Page
templates own page markup, page-specific behavior, and genuinely page-specific
CSS, not duplicate shared CSS or error-rendering logic.

### Exact Prototype Parity Without Transport Inference

Each affected runtime page matches frozen prototype DOM structure, order,
classes, actions, labels, default open state, responsive layout, themes,
keyboard behavior, and visible loading/empty/error/success states. Request and
response shapes remain owned by existing Pydantic models, routes,
`/openapi.json`, and tests.

### Small Vertical Full-Stack Slices

Shared shell lands first. Pipeline Settings, API Providers, LLM Configuration,
Prompt Management, System/Data Backup, Runs, Run Details, Scans, Candidate
Profiles, Bookmarks, Synonyms, and Preference Optimization then land
sequentially. Each slice wires
one prototype flow to real backend behavior and passes focused frontend,
backend, contract, and independent validator proof before next slice starts.

### Temporary Integration Mapping Removed Safely

`docs/fitcv-settings-ui-prototype.integration.md` records only unresolved
contract-to-UI mappings and acceptance evidence. It references canonical
schemas rather than copying them. Resolved entries are removed after each
slice. Final file deletion requires all slices to pass and explicit disposition
approval because file is current user-restored work; without approval, retain
only unresolved mappings.

## Execution Approach

- Mode: `inline sequential`
- Executor: `codex` by default; `DeepAgents` only through `dcode-project --role normal --no-mcp` for bounded read-only or explicitly selected local work
- Required skills: `skill-executing-plans`, `skill-test-driven-development`,
  `skill-frontend-component-engineering`, `skill-full-stack-integration`,
  `skill-backend-verification`, `ui-ux-pro-max`,
  `skill-requesting-code-review`, `skill-verification-before-completion`
- Isolation: current approved lane or user-approved worktree; never silently
  create, switch, merge, clean, stash, or delete lane
- Commit policy: no commits unless separately authorized
- Parallel ownership: none; `base.html`, `app.py`, and shared tests create hidden
  dependencies across slices
- Sequential fallback: exact task order below
- Proof-only rule: a Gate 0 `already aligned` disposition makes that slice
  proof-only. Run focused tests and validator first; edit only exact drift named
  by failed proof. A `change narrowly` disposition limits edits to named drift.
- Shared-write control: Task 1 is sole owner of shared shell CSS and async-state
  primitives. Later tasks may retain page-specific CSS but must not add local
  copies of shared selectors or shared state rendering.
- Prototype freeze command:
  `git hash-object docs/fitcv-settings-ui-prototype.html`
- Required prototype result:
  `989af611bd7767c148022c79ac00c5069d8a3956`
- Contract discovery: inspect live `/openapi.json`, Pydantic models, routes, and
  focused tests before each slice. Do not create duplicate TypeScript schemas,
  mock registries, or OpenAPI files.
- Context7: use only when pinned project sources do not answer version-specific
  FastAPI, Jinja, or browser-library question.
- Specmatic: use only against canonical `/openapi.json` for examples or
  conformance when route contract evidence needs it; never use it to define UI
  or replace direct backend tests.

## Coordination State

- Coordination owner: `single lead controller`
- Branch: `main`
- Base commit: `488914851a072a362187f7c785665e4b05bb5b65`
- Active task(s): none; final verification complete; all 13 slice validators passed.
- Expected workspace: preserve all existing launcher, governance, skill, and
  test changes outside this plan; this plan is current controller-owned change.
- Checkpoint: `none`; no task-local acceptance commit exists.
- Next action: controller Git disposition only; do not commit, merge, push, clean,
  or delete worktrees without separate authorization.
- Blockers: none for this closed lane. Approved deferral: prototype Pipeline
  hash-section/deep-link parity (`#screening`, `#ranking`, and related sections)
  remains for the upcoming plan; current lane does not claim that work complete.
  Fresh final evidence: declared suite `1046 passed, 2 skipped`;
  Task 7 lifecycle/frontend focused suite `11 passed, 436 deselected`; Task 7
  declared suite `34 passed, 578 deselected`; normal and packaged-local OpenAPI
  `200`, each with `131` paths and required `Idempotency-Key` on all three bulk
  lifecycle routes; prototype hash
  `989af611bd7767c148022c79ac00c5069d8a3956`; `compileall` and
  `git diff --check` passed. Packaged-local browser evidence covered all 14
  navigation routes at `1440x900` and `375x812`, light/dark themes, titles/H1s,
  no horizontal overflow, Active/Archived URL state, empty states, Trigger Run
  dialog, disabled submit, Escape focus return, and zero console errors.
- Residual risk: deferred settings section parity remains unresolved by design;
  aggregate evidence does not replace each task's required
  validator; browser evidence covers declared route matrix and interactions,
  not every slice-specific async/error/retry state or a source-to-prototype
  structural diff for every component; no claim of universal no-drift is made.

| Task | State | Executor Profile | Validator Profile | Depends On | Required Evidence |
| --- | --- | --- | --- | --- | --- |
| Task 1 | `complete` | `normal` | `high` | none | focused lifecycle/local-route/shell proof: `17 passed, 451 deselected`; validator PASS; prototype hash matches |
| Task 2 | `complete` | `normal` | `high` | Task 1 | focused settings proof: `260 passed, 1 skipped, 395 deselected`; validator PASS; prototype hash matches |
| Task 3 | `complete` | `normal` | `xhigh` | Task 2 | focused provider proof: `7 passed, 476 deselected`; validator PASS; prototype hash matches |
| Task 4 | `complete` | `normal` | `xhigh` | Task 3 | focused async UI proof: `1 passed, 37 deselected`; backend node: `1 passed`; validator PASS; prototype hash matches |
| Task 5 | `complete` | `high` | `xhigh` | Task 4 | focused proof: `3 passed, 480 deselected`; duplicate-style and compatibility-redirect regression: `2 passed`; validator PASS; prototype hash matches |
| Task 6 | `complete` | `high` | `xhigh` | Task 5 | focused backend/import proof: `7 passed, 48 deselected`; validator PASS; prototype hash matches |
| Task 7 | `complete` | `high` | `xhigh` | Task 6 | declared suite: `34 passed, 578 deselected`; lifecycle/frontend focused suite: `11 passed, 436 deselected`; backend and frontend xhigh validators PASS; OpenAPI header contract PASS |
| Task 8 | `complete` | `high` | `xhigh` | Task 7 | run-detail action/reconciliation proof: `3 passed`; validator PASS |
| Task 9 | `complete` | `high` | `xhigh` | Task 8 | scan proof: `32 passed, 413 deselected`; validator PASS |
| Task 10 | `complete` | `high` | `xhigh` | Task 9 | candidate-profile proof: `6 passed, 543 deselected`; validator PASS |
| Task 11 | `complete` | `high` | `xhigh` | Task 10 | bookmark/interest proof: `3 passed, 546 deselected`; validator PASS |
| Task 12 | `complete` | `high` | `xhigh` | Task 11 | synonym-policy proof: `13 passed, 576 deselected`; validator PASS |
| Task 13 | `complete` | `high` | `xhigh` | Task 12 | optimization proof: `4 passed`; validator PASS; prototype hash matches |

Task IDs, dependencies, canonical execution mode, and planned paths are in
frontmatter. This ledger owns only static controller task state. Git owns
workspace identity, active commit, and change evidence.

Each task includes this plan in `allowed_paths` and `planned_write_paths` only
for its controller-owned ledger transition after fresh task-local proof. It
does not authorize task-scope, requirement, or acceptance-criterion changes.

## Common Slice Protocol

### Prototype Parity Matrix

Before editing each slice, record in
`docs/fitcv-settings-ui-prototype.integration.md`:

- prototype renderer or markup owner;
- runtime route and template;
- exact DOM hierarchy, child order, classes, actions, labels, and default
  expanded/collapsed state;
- desktop and `375px` behavior;
- light and dark theme behavior;
- keyboard path and focus return;
- empty, loading, error, success, and stale/refreshing states applicable to flow;
- canonical backend operations and contract owner references;
- current mismatch list and affected source owners.

Do not copy request or response schemas into sidecar.

### Backend Proof Contract

Every backend-consuming slice must run `skill-backend-verification` and record:

- nearest direct boundary exercised with success;
- trust-boundary validation failure;
- conflict, stale revision, duplicate submission, or idempotency behavior where
  operation supports it;
- final persisted state or side effect;
- rollback or consistent state after failed mutation;
- real SQLite, filesystem, queue, or provider dependency failure where material;
- canonical `/openapi.json` operation evidence when route is schema-owned;
- one representative operation reconstructed through existing resource ID,
  revision, event, or test instrumentation when traceability is
  material;
- fresh command, exit code, failures, and skips.

Browser proof extends this evidence and never replaces it.

Every task must map each applicable Backend Proof bullet to exact existing or
intended pytest node IDs before implementation. Broad `-k` selection is a
convenience command, not proof ownership. New intended node IDs must be added to
the task before code changes and must cover success, validation, persisted state
or side effect, conflict/idempotency, and dependency failure by applicability.

### Backend Proof Node Ownership

- Task 1: intended `tests/test_fitcv_cp/test_local_routes.py::test_shared_shell_matches_frozen_prototype_and_canonical_error_contract`, `::test_local_system_redirects_to_admin_system`, and `tests/test_fitcv_cp/test_lifecycle_removal.py::test_lifecycle_page_route_is_removed_and_status_resource_remains`.
- Task 2: `tests/test_fitcv_cp/test_app.py::test_get_pipeline_settings_returns_effective_resource`, `::test_patch_pipeline_settings_uses_atomic_mutation`, `::test_patch_pipeline_settings_rejects_excluded_key`, `::test_patch_pipeline_settings_rejects_stale_revision`, `::test_reset_pipeline_settings_uses_atomic_mutation`.
- Task 3: `tests/test_fitcv_cp/test_local_app.py::test_packaged_provider_api_supports_verified_connection_and_models`, `::test_packaged_provider_api_rejects_stale_revision_and_unsafe_origin`.
- Task 4: `tests/test_fitcv_cp/test_local_app.py::test_packaged_llm_configuration_is_revisioned_and_local_only`.
- Task 5: nodes listed in Task 5 Verification and Backend Proof.
- Task 6: `tests/test_fitcv_cp/test_local_app.py::test_packaged_system_settings_are_revisioned_validated_and_local_only`, `tests/test_fitcv_cp/test_local_routes.py::test_backup_rejects_active_work`, `::test_data_page_and_backup_download`, `::test_awaiting_continue_run_blocks_backup_and_shutdown`.
- Task 7: `tests/test_fitcv_cp/test_app.py::test_managed_run_requires_upload_or_scan_and_accepts_scan_only`, `::test_real_managed_run_preserves_upload_then_selected_scan_order`, `::test_real_managed_run_rejects_missing_archived_empty_and_integrity_invalid_sources`, `::test_delete_archived_runs_is_idempotent_and_returns_deleted_ids`, `::test_delete_archived_runs_reports_all_or_nothing_conflict`.
- Task 8: `tests/test_fitcv_cp/test_app.py::test_get_run_detail_not_found`, `::test_get_run_detail_reconciles_orphaned_running_run_when_queue_job_missing`, `::test_run_detail_queued_shows_stop_run`, `::test_run_detail_terminal_statuses_show_archive_run`.
- Task 9: `tests/test_fitcv_cp/test_scan_contracts.py::test_scan_create_request_rejects_empty_company_selection`, `::test_derive_scan_capabilities_owns_all_action_rules`, `::test_validate_scan_transition_rejects_invalid_transition`, `tests/test_fitcv_cp/test_app.py::test_mock_scan_creation_replays_same_scan_for_same_idempotency_key`, `::test_mock_scan_lifecycle_rejects_stale_revision`, `::test_mock_scan_ui_covers_error_pending_and_integrity_states`.
- Task 10: `tests/test_fitcv_cp/test_app.py::test_candidate_profile_real_app_routes_process_yaml_through_staged_lifecycle`, `::test_candidate_profile_real_app_routes_accept_supported_non_yaml_formats`, `tests/test_fitcv_cp/test_sqlite_store.py::test_candidate_profile_retry_resumes_failed_processing_stage`, `::test_candidate_profile_review_and_confirmation_are_cas_and_idempotent`, `::test_candidate_profile_confirmation_failure_rolls_back`.
- Task 11: `tests/test_fitcv_cp/test_app.py::test_bookmark_and_interest_actions_use_run_job_identity`, `::test_bookmark_interest_clear_and_stale_rating_contract`, `tests/test_fitcv_cp/test_sqlite_store.py::test_bookmark_query_selection_and_removal_share_filtered_intersection`.
- Task 12: `tests/test_fitcv_cp/test_app.py::test_synonym_policy_routes_read_activate_and_persist_invalid_draft`, `::test_synonym_approve_forwards_policy_revisions`, `tests/test_fitcv_cp/test_sqlite_store.py::test_synonym_approval_rolls_back_policy_and_decision_when_processing_log_fails`, `::test_synonym_approval_rejects_stale_policy_revision`.
- Task 13: `tests/test_fitcv_cp/test_optimization_page.py::test_candidate_post_uses_submitted_compare_tokens_and_prg`, `::test_public_run_mutations_use_server_actor_and_baseline_guards`, `::test_public_run_inactivation_requires_confirmation_and_uses_active_snapshot`, `::test_public_run_remove_hides_non_active_run_and_rejects_active_owner`, plus relevant SQLite activation/inactivation nodes.

### Shared Async-State Contract

Task 1 extends existing `base.html` runtime helpers with one function:

`fitcvRenderAsyncState(target, state)`

`state` contains `kind`, `message`, `code`, `action`, `retry`, and
`preserveContent`. `kind` is one of `pending`, `success`, `empty`, `error`,
`retryable`, `non_retryable`, `stale`, or `refreshing`. Pages own resource state
and retry callbacks; shared code owns consistent rendering, live-region
semantics, focus target, and preservation of last valid content.

### Independent Validator Agent Checkpoint

After Task 1 and after every capability slice, stop implementation and launch a
fresh validator agent. Validator is read-only. Any failure returns to current
slice owner; after fixes, launch another fresh validator rather than reusing same
agent.

Prefix this prompt with exact completed task number and title. Validator reads
that task's prototype owner, routes, templates, backend commands, and contract
checks directly from this plan:

```text
Validate only completed task named immediately above. Do not edit files.

UI truth is frozen prototype blob 989af611bd7767c148022c79ac00c5069d8a3956.
First run `git hash-object docs/fitcv-settings-ui-prototype.html`; stop on mismatch.
Transport truth is current FastAPI/Pydantic source, registered routes,
`/openapi.json`, `docs/api.md`, and focused tests. Do not infer payloads from
prototype.

Compare prototype owner with runtime routes and templates named in completed
task. Verify exact DOM hierarchy, child order, classes, actions, labels,
button variants, default expanded state, and forbidden extra controls. Verify
desktop 1440x900 and 375x812, light/dark, keyboard-only navigation, visible
focus, focus return, reduced motion, long content, empty/loading/error/success,
and stale/retry states applicable to this slice. Use Playwright accessibility
snapshots and screenshots; use Chrome DevTools only for console, network, or
computed-style diagnosis. Never use port 8765.

Run backend commands and contract checks named in completed task. Browser success
cannot compensate for missing backend proof.

Report PASS or FAIL. For every failure give route, viewport/theme/state,
selector or accessible name, expected prototype structure, actual runtime
structure, owning file, screenshot path, and missing backend/contract evidence.
Confirm no unrelated file changed.
```

### Validator Exit Gate

- prototype hash matches exactly;
- no hierarchy, order, class, label, action, expanded-state, or forbidden-extra
  mismatch remains;
- Playwright evidence exists for both viewports and themes;
- keyboard/focus and applicable async states pass;
- focused frontend tests pass;
- direct backend proof and contract evidence pass;
- browser console has no uncaught errors;
- sidecar contains only unresolved mappings;
- unrelated working-tree files remain untouched.

## Gate 0: Freeze Complete Drift Ledger

Before Task 1 edits any runtime file, audit every route listed in this plan and
record confirmed differences in `docs/fitcv-settings-ui-prototype.integration.md`.
Ledger must cover visual structure, order, classes, copy, controls, navigation,
interaction, validation, responsive behavior, themes, keyboard/focus, and
empty/loading/error/success/stale states. Each row names prototype owner,
runtime owner, transport owner, affected tests, and disposition: `change`,
`already aligned`, or `not applicable`. Prompt Management starts as `change`
from confirmed audit above. “Already aligned” requires DOM and Playwright proof;
absence of reported drift is not proof. No runtime edit begins until ledger is
complete and prototype hash matches.

## Task Breakdown

### Task 1: Align Shared Shell And Async States

**Purpose:**
- establish one shared runtime CSS, navigation/header, and async-state owner before page work starts

**Specification Coverage:**
- frozen prototype shell at `docs/fitcv-settings-ui-prototype.html:100`
- `docs/operating_system/rules/frontend-ui-rule.md`
- `docs/operating_system/rules/frontend-backend-integration-rule.md`

**Required Skills:**
- `skill-test-driven-development`
- `skill-frontend-component-engineering`
- `skill-full-stack-integration`
- `skill-backend-verification`
- `ui-ux-pro-max`

**Files And Symbols:**
- Inspect: `docs/fitcv-settings-ui-prototype.html` shell, navigation, header, dialogs, shared classes, theme, responsive rules
- Modify: `src/fitcv_cp/templates/base.html` shared CSS, sidebar, header, `fitcvApiRequest`, shared ready initializer, shared async-state renderer
- Modify: `tests/test_fitcv_cp/test_local_routes.py` shell/navigation/component contract tests
- Modify: `tests/test_fitcv_cp/test_app.py` shared initializer and canonical error rendering tests
- Modify: `src/fitcv_cp/local_routes.py` `local_system` compatibility redirect
- Modify: `src/fitcv_cp/app.py` Lifecycle page route removal
- Delete: `src/fitcv_cp/templates/lifecycle.html`
- Create: `tests/test_fitcv_cp/test_lifecycle_removal.py` narrow page-removal regression
- Modify: `docs/fitcv-settings-ui-prototype.integration.md` shell mapping only
- Verify: `/admin/runs`, `/admin/scans`, `/admin/candidate-profiles`, `/admin/bookmarks`, `/admin/synonyms`, `/admin/settings`, `/admin/api-providers`, `/admin/llm-configuration`, `/admin/settings/prompt-management`, `/admin/system`, `/local/system`, `/admin/lifecycle`, and `/local/lifecycle/status`

**Dependencies:**
- frozen prototype hash verified
- working-tree snapshot recorded with `git status --short`
- no other parent-plan task active

**Steps:**
- [ ] Add failing structural and route tests for prototype navigation order, group placement, Prompt Management presence, Lifecycle absence, header action order, mobile menu semantics, shared page container, `/local/system` redirect, Lifecycle page-route absence, and preserved status resource.
- [ ] Remove `/admin/lifecycle` page route and `lifecycle.html`; redirect `/local/system` to `/admin/system`; retain `/local/lifecycle/status` and shutdown-dialog use only.
- [ ] Consolidate only shared runtime CSS in `base.html`; later slice templates remove duplicate shared selectors but retain genuinely page-specific CSS. Add no CSS build system or dependency.
- [ ] Extend existing request path with `fitcvRenderAsyncState(target, state)` using the Shared Async-State Contract. Preserve canonical code, message, action, HTTP status, and prior valid data.
- [ ] Provide shared duplicate-submit lock, retry callback binding, live-region semantics, and focus target without owning page-specific state.
- [ ] Remove resolved shell entries from sidecar; retain exact unresolved items.
- [ ] Run fresh independent validator checkpoint.

**Verification:**
- [ ] `uv run pytest tests/test_fitcv_cp/test_local_routes.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_lifecycle_removal.py -q -k "navigation or shell or initializer or api_error or packaged_local_pages or lifecycle or local_system"`
- Expected: focused shared-shell, redirect, removal, and error tests pass.
- [ ] Playwright: all listed routes at `1440x900` and `375x812`, light/dark, menu keyboard path, focus visibility, reduced motion, no horizontal overflow.
- Expected: exact prototype shell and no Lifecycle link; `/local/system` redirects to `/admin/system`; `/admin/lifecycle` has no page route; `/local/lifecycle/status` remains reachable only as status resource.

**Backend Proof:**
- Direct boundary: canonical error envelope from one success route, one `422`, one `404`, and one `409` response through TestClient.
- State: no mutation for failed requests; request metadata remains available to shared renderer.
- Direct boundary: `/local/system` returns `302` to `/admin/system`; `/admin/lifecycle` returns no page route; `/local/lifecycle/status` retains its current JSON status contract.
- Contract evidence: `docs/api.md#contract-conventions`, `ApiError` handlers in `src/fitcv_cp/app.py`, `/openapi.json`.

**Sidecar Lifecycle:**
- Add shell operation/state mapping before edits; remove resolved items after validator PASS. Do not delete sidecar.

**Exit Criteria:**
- one shared runtime CSS/async-state owner exists; page-specific CSS remains local without shared-selector duplication; shell validator passes before Task 2 starts.

### Task 2: Align Pipeline Settings

**Purpose:**
- match prototype Pipeline sections while preserving schema-owned settings and revision-safe mutation

**Specification Coverage:**
- prototype Pipeline navigation and section renderer
- existing settings projection and PATCH/reset contracts

**Required Skills:**
- `skill-test-driven-development`
- `skill-frontend-component-engineering`
- `skill-full-stack-integration`
- `skill-backend-verification`
- `ui-ux-pro-max`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/settings_schema.py:pipeline_settings_projection`
- Inspect: `src/fitcv_cp/app.py:_pipeline_settings_resource`, `get_pipeline_settings`, `patch_pipeline_settings`, `reset_pipeline_settings`, `admin_settings_view`, `admin_settings_section`
- Modify: `src/fitcv_cp/templates/settings.html`
- Modify: `tests/test_fitcv_cp/test_local_routes.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify only when projection defect is proven: `tests/test_fitcv_cp/test_settings_schema.py`, `src/fitcv_cp/settings_schema.py`
- Verify: `tests/test_fitcv_cp/test_settings_store.py`, `docs/api.md` Pipeline operations, `/openapi.json`

**Dependencies:**
- Task 1 validator PASS

**Steps:**
- [ ] Freeze exact prototype section order, headings, descriptions, control shapes, Manage dialogs, action order, and default open state in focused tests.
- [ ] Render current `pipeline_settings_projection` through exact prototype structures; do not duplicate field inventory in template JavaScript.
- [ ] Use shared pending/error/stale renderer for direct controls, group saves, and reset; preserve prior server values during refresh and restore values on failure.
- [ ] Keep one revision owner and one mutation lock for shared Pipeline resource.
- [ ] Prove reset confirmation, validation errors, revision conflict, retry, and success states.
- [ ] Remove resolved Pipeline entries from sidecar.
- [ ] Run fresh independent validator checkpoint.

**Verification:**
- [ ] `uv run pytest tests/test_fitcv_cp/test_local_routes.py tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_settings_store.py tests/test_fitcv_cp/test_app.py -q -k "pipeline_settings or pipeline_projection or prototype_component_contract"`
- Expected: projection, route, persistence, and DOM contract tests pass.
- [ ] Playwright: every Pipeline route at both viewports/themes; keyboard dialog open/cancel/save; validation, pending, stale, retry, reset, success.

**Backend Proof:**
- Direct boundary: `GET /settings/pipeline`, `PATCH /settings/pipeline`, `POST /settings/pipeline/actions/reset`.
- Failure: excluded/retired key validation and stale revision conflict.
- State: atomic settings persistence; failed mutation leaves revision/value unchanged.
- Contract evidence: `docs/api.md` Pipeline Settings and `/openapi.json`.

**Sidecar Lifecycle:**
- Keep operation names and UI state mapping only; remove Pipeline section after validator PASS.

**Exit Criteria:**
- all Pipeline pages match prototype and use real revisioned resource without second frontend schema.

### Task 3: Align API Providers

**Purpose:**
- restore prototype provider list/detail interactions and connect every action to current packaged-local provider contracts

**Specification Coverage:**
- `renderApiProvidersPage`, `renderProviderDetailsPage`
- provider collection, detail, connection, model, verification routes

**Required Skills:**
- `skill-test-driven-development`
- `skill-frontend-component-engineering`
- `skill-full-stack-integration`
- `skill-backend-verification`
- `ui-ux-pro-max`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/app.py` provider Pydantic models and routes
- Inspect: `src/fitcv_cp/provider_registry.py`
- Inspect: `src/fitcv_cp/local_credentials.py`
- Modify: `src/fitcv_cp/templates/api_providers.html`
- Modify: `src/fitcv_cp/templates/api_provider_detail.html`
- Modify: `tests/test_fitcv_cp/test_local_routes.py`
- Modify: `tests/test_fitcv_cp/test_local_app.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Verify: packaged-local `/openapi.json` provider operations

**Dependencies:**
- Task 2 validator PASS

**Steps:**
- [ ] Lock prototype search, provider grouping, collapsed/expanded sections, separate compatible add actions, detail hierarchy, dialogs, button order.
- [ ] Bind list/detail/search and connection/model mutations to existing routes; do not infer fields from prototype sample data.
- [ ] Use shared states for first load, empty registry, pending verification, validation error, provider failure, stale revision, retry, success.
- [ ] Preserve entered non-secret values after validation errors; never echo stored credentials.
- [ ] Remove resolved API Provider entries from sidecar.
- [ ] Run fresh independent validator checkpoint.

**Verification:**
- [ ] `uv run pytest tests/test_fitcv_cp/test_local_routes.py tests/test_fitcv_cp/test_local_app.py tests/test_fitcv_cp/test_app.py -q -k "provider"`
- Expected: local-only boundary, origin validation, revision conflict, provider mutations, template contracts pass.
- [ ] Playwright: list/search/detail/add/edit/delete/verify at both viewports/themes, keyboard dialogs, empty/loading/error/success/stale states.

**Backend Proof:**
- Direct boundary: provider collection/detail plus connection/model mutation and verification routes.
- Failure: unsafe origin, invalid provider/model, verification dependency failure, stale revision.
- State: successful mutation persists; failed verification does not corrupt prior state or expose secrets.
- Contract evidence: packaged-local `/openapi.json` and focused route tests.

**Sidecar Lifecycle:**
- Reference provider operation IDs and UI states; remove slice entries after validator PASS.

**Exit Criteria:**
- provider pages match prototype and all visible actions have proven real backend behavior.

### Task 4: Align LLM Configuration

**Purpose:**
- preserve already-close layout while closing remaining prototype and async-state drift without rebuilding confirmed components

**Specification Coverage:**
- `renderLlmConfigurationPage`
- revisioned LLM task-routing resource

**Required Skills:**
- `skill-test-driven-development`
- `skill-full-stack-integration`
- `skill-backend-verification`
- `ui-ux-pro-max`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/app.py:get_llm_configuration`, `patch_llm_configuration_route`, response models
- Inspect: `src/fitcv_cp/provider_registry.py`
- Modify: `src/fitcv_cp/templates/llm_configuration.html`
- Modify: `tests/test_fitcv_cp/test_local_routes.py`
- Modify: `tests/test_fitcv_cp/test_local_app.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Verify: Candidate Profile LLM task mapping in `docs/superpowers/specs/2026-08-01-23-49-canonical-candidate-uniform-evidence-projection-spec.md`

**Dependencies:**
- Task 3 validator PASS

**Steps:**
- [ ] Freeze current parity-aligned rows/dialogs; add tests only for confirmed remaining hierarchy, copy, action, and state differences.
- [ ] Reuse provider/model options from server resource; keep unavailable model state visible without inventing fallback payloads.
- [ ] Use shared pending/error/stale renderer and disable duplicate mutation.
- [ ] Preserve task dialog focus and values on validation failure.
- [ ] Remove resolved LLM Configuration entries from sidecar.
- [ ] Run fresh independent validator checkpoint.

**Verification:**
- [ ] `uv run pytest tests/test_fitcv_cp/test_local_routes.py tests/test_fitcv_cp/test_local_app.py tests/test_fitcv_cp/test_app.py -q -k "llm_configuration"`
- Expected: local-only, revisioned, validated route and prototype copy pass.
- [ ] Playwright: default model and one Candidate Profile task at both viewports/themes, keyboard dialog, missing model, pending, validation, stale/retry, success.

**Backend Proof:**
- Direct boundary: `GET /llm-configuration`, `PATCH /llm-configuration`.
- Failure: invalid/unavailable model and stale revision.
- State: successful task route persists; failed mutation preserves prior revision and task mapping.
- Contract evidence: packaged-local `/openapi.json`, response models, route tests.

**Sidecar Lifecycle:**
- Keep only task-to-control state mapping; remove resolved entries after validator PASS.

**Exit Criteria:**
- LLM Configuration retains confirmed UI and completes real revision-safe state handling.

### Task 5: Align Prompt Management

**Purpose:**
- replace confirmed runtime drift with prototype Prompt Management hierarchy and shared prompt-dialog behavior while preserving backend-owned prompt contracts

**Specification Coverage:**
- prototype `renderPromptManagementPage`, `promptTaskRowMarkup`, and shared stage prompt dialog
- revisioned Prompt Configuration collection and mutation routes

**Required Skills:**
- `skill-test-driven-development`
- `skill-frontend-component-engineering`
- `skill-full-stack-integration`
- `skill-backend-verification`
- `ui-ux-pro-max`

**Files And Symbols:**
- Inspect: `docs/fitcv-settings-ui-prototype.html:1648` `renderPromptManagementPage`, prompt row markup, prompt dialog
- Inspect: `src/fitcv_cp/app.py:_prompt_configuration_resource`, `get_prompt_configurations`, `patch_prompt_configuration_route`, `admin_prompt_management`, `admin_settings_section`
- Modify: `src/fitcv_cp/templates/prompt_management.html`
- Modify: `tests/test_fitcv_cp/test_local_routes.py`
- Modify: `tests/test_fitcv_cp/test_local_app.py` only if backend behavior lacks exact proof
- Modify: `tests/test_fitcv_cp/test_app.py` only if shared prompt runtime behavior lacks exact proof
- Verify: `/admin/settings/prompt-management`, `/admin/prompt-management`, `GET /prompt-configurations`, `PATCH /prompt-configurations/{task_id}`

**Dependencies:**
- Task 4 validator PASS

**Confirmed Drift Inventory:**
- Runtime uses `workspace-stack`/`page-header`; prototype uses `page-head` with `Pipeline` eyebrow.
- Runtime description differs from approved prototype copy.
- Runtime groups raw backend values dynamically; prototype renders fixed `Pipeline Prompts` then `Synonym Prompts` sections in that order.
- Runtime uses plain `section-card` and `settings-row`; prototype uses `section-card llm-config-card` and shared LLM route rows.
- Runtime manage dialog and button structure differ from prototype shared prompt dialog.
- Existing tests assert route/content presence and backend conflicts, not full DOM/action/dialog parity.

**Steps:**
- [ ] Add failing `test_prompt_management_matches_frozen_prototype_contract` covering page head, eyebrow, approved copy, section order/classes, row actions, labels, and shared dialog structure.
- [ ] Render backend resources through prototype-owned section and row structure without copying prompt schema or deriving backend groups from sample markup.
- [ ] Reuse shared prompt dialog and Task 1 async-state renderer for initial load, validation, stale revision, retry, default reset, and save success.
- [ ] Preserve entered replacement on `422`; preserve last valid resource on `409`; prevent duplicate PATCH submission.
- [ ] Keep `/admin/prompt-management` as direct compatibility redirect and `Prompt Management` visible under Pipeline.
- [ ] Remove resolved Prompt Management entries from sidecar.
- [ ] Run fresh independent validator checkpoint.

**Verification:**
- [ ] `uv run pytest tests/test_fitcv_cp/test_local_routes.py tests/test_fitcv_cp/test_local_app.py tests/test_fitcv_cp/test_app.py -q -k "prompt_management or prompt_configuration or prompt_reset"`
- Exact proof nodes: `tests/test_fitcv_cp/test_local_routes.py::test_prompt_management_matches_frozen_prototype_contract` (intended), `tests/test_fitcv_cp/test_local_routes.py::test_packaged_local_admin_pages_render_canonical_resources`, `tests/test_fitcv_cp/test_local_routes.py::test_packaged_local_pages_encode_approved_ui_states`, `tests/test_fitcv_cp/test_local_app.py::test_packaged_prompt_configuration_exposes_defaults_and_validates_replacements`, `tests/test_fitcv_cp/test_local_app.py::test_packaged_prompt_configuration_resets_custom_replacement_to_default` (intended).
- [ ] Playwright: both prompt sections, manage/reset/save dialog flow, keyboard/focus return, long prompt text, pending/validation/conflict/retry/success at both viewports/themes.

**Backend Proof:**
- Success, validation, conflict, and persisted replacement: `tests/test_fitcv_cp/test_local_app.py::test_packaged_prompt_configuration_exposes_defaults_and_validates_replacements`.
- Successful persisted default reset: intended `tests/test_fitcv_cp/test_local_app.py::test_packaged_prompt_configuration_resets_custom_replacement_to_default`.
- Local-only page and compatibility route: `tests/test_fitcv_cp/test_local_routes.py::test_packaged_local_admin_pages_render_canonical_resources` plus direct redirect assertion added to intended DOM contract test.
- Contract evidence: route functions and response models in `src/fitcv_cp/app.py`; packaged-local `/openapi.json` where registered. Do not create parallel prompt schema.
- Dependency failure: not applicable; prompt configuration is local revisioned persistence with no provider call.

**Sidecar Lifecycle:**
- Add exact Prompt Management operation/state mappings before edits; remove resolved entries after validator PASS.

**Exit Criteria:**
- Prompt Management matches frozen prototype structure and shared dialog behavior; revision-safe backend mutation remains canonical and directly proven.

### Task 6: Align System And Data Backup

**Purpose:**
- match prototype Data & Backup, Request Retry, and Worker Recovery sections and prove local filesystem/state behavior directly

**Specification Coverage:**
- `renderSystemPage`
- local backup/import and revisioned system settings routes

**Required Skills:**
- `skill-test-driven-development`
- `skill-full-stack-integration`
- `skill-backend-verification`
- `ui-ux-pro-max`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/app.py:get_system_settings`, `patch_system_settings_route`, admin System route
- Inspect: `src/fitcv_cp/local_routes.py` backup download/import handlers
- Inspect: `src/fitcv_cp/local_storage.py`
- Create: `src/fitcv_cp/templates/_data_backup_panel.html` as the single shared Data & Backup markup owner
- Modify: `src/fitcv_cp/templates/system.html` to include `_data_backup_panel.html`
- Modify: `src/fitcv_cp/templates/local_data_backup.html` to include `_data_backup_panel.html` on compatibility route
- Modify: `tests/test_fitcv_cp/test_local_routes.py`
- Modify: `tests/test_fitcv_cp/test_local_app.py`
- Modify: `tests/test_fitcv_cp/test_app.py`

**Dependencies:**
- Task 5 validator PASS

**Steps:**
- [ ] Lock prototype section order/default state: Data & Backup visible, Request Retry open, Worker Recovery closed.
- [ ] Replace static form hierarchy with exact prototype structures while keeping existing setting names and validation bounds from backend models.
- [ ] Move existing Data & Backup markup into `_data_backup_panel.html`; both routes include it and keep one operation implementation.
- [ ] Use shared pending/error/stale renderer for settings save, backup download, import validation, active-work conflict, restart handoff, retry.
- [ ] Remove resolved System entries from sidecar.
- [ ] Run fresh independent validator checkpoint.

**Verification:**
- [ ] `uv run pytest tests/test_fitcv_cp/test_local_routes.py tests/test_fitcv_cp/test_local_app.py tests/test_fitcv_cp/test_app.py -q -k "system_settings or backup or import or data_page"`
- Expected: revision, validation, unsafe archive, active-work conflict, download, import, DOM contract tests pass.
- [ ] Playwright: System and direct Data Backup route at both viewports/themes; keyboard details, file chooser cancellation, loading/error/success/stale.

**Backend Proof:**
- Direct boundary: `GET/PATCH /system-settings`, backup download, backup import.
- Failure: invalid numeric bounds, stale revision, active-work conflict, unsafe archive, filesystem/import failure.
- State: settings persist atomically; rejected import leaves current database untouched; accepted import records restart handoff.
- Contract evidence: packaged-local `/openapi.json`, local route tests, filesystem assertions.

**Sidecar Lifecycle:**
- Reference system and local backup operations; remove slice entries after validator PASS.

**Exit Criteria:**
- System and compatibility Data Backup route share one prototype-aligned component contract and proven local behavior.

### Task 7: Align Runs List And Trigger Run

**Purpose:**
- match prototype Runs table, filters, bulk actions, Trigger Run dialog while preserving managed upload/scan contracts

**Specification Coverage:**
- `renderRunsPage`, `renderRunScanPicker`
- `POST /runs`, `GET /runs`, run lifecycle actions

**Required Skills:**
- `skill-test-driven-development`
- `skill-frontend-component-engineering`
- `skill-full-stack-integration`
- `skill-backend-verification`
- `ui-ux-pro-max`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/app.py` `trigger_run`, `get_runs_list`, admin Runs route, archive/unarchive/cancel/delete-preview handlers
- Inspect: `src/fitcv_cp/models.py` run request models
- Inspect: `src/fitcv_cp/store.py`, `src/fitcv_cp/sqlite_store.py`, `src/fitcv_cp/queue.py`
- Modify: `src/fitcv_cp/templates/runs_list.html`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify/Verify: `tests/test_fitcv_cp/test_queue.py`, `tests/test_fitcv_cp/test_store.py`, `tests/test_fitcv_cp/test_sqlite_store.py`, `docs/api.md`

**Dependencies:**
- Task 6 validator PASS

**Steps:**
- [ ] Freeze prototype page head, tabs, counts, filters, table order, action bar, empty state, pagination, Trigger Run dialog structure.
- [ ] Preserve URL-owned lifecycle/filter/page state and browser Back/Forward.
- [ ] Bind upload, scan selection, source ordering, submission, bulk lifecycle, preview-delete, conflict states to existing routes.
- [ ] Use shared pending/error/retry/stale renderer and prevent duplicate run submission with one idempotency key per user attempt.
- [ ] Keep prior list data during refresh and reconcile missing/archived scan selections without losing valid upload input.
- [ ] Remove resolved Runs entries from sidecar.
- [ ] Run fresh independent validator checkpoint.

**Verification:**
- [ ] `uv run pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_queue.py tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_sqlite_store.py -q -k "trigger_run or get_runs_list or admin_runs or managed_run or bulk_archive or delete_archived"`
- Expected: run creation, source order, idempotency/conflict, list, lifecycle, persistence, template tests pass.
- [ ] Playwright: active/archived tabs, empty/list/loading/error, Trigger Run with upload-only/scan-only/combined, stale scan reconciliation, keyboard, both viewports/themes.

**Backend Proof:**
- Direct boundary: `POST /runs`, `GET /runs`, lifecycle and delete-preview routes.
- Failure: missing source validation, unavailable scan, local busy conflict, persistence failure, queue/enqueue failure.
- State: run inserted before enqueue; failed bundle persistence leaves consistent state; duplicate submission does not create duplicate run.
- Bulk lifecycle idempotency: `tests/test_fitcv_cp/test_app.py::test_admin_bulk_archive_replays_without_duplicate_mutation_or_events`, `::test_admin_bulk_lifecycle_rejects_idempotency_conflict`, `::test_admin_bulk_lifecycle_requires_idempotency_key`.
- Frontend retry contract: `tests/test_fitcv_cp/test_app.py::test_runs_list_bulk_lifecycle_retries_with_same_idempotency_key`.
- Contract evidence: `docs/api.md`, `/openapi.json`, route/store tests.
- Trace: reconstruct created run through run ID and queue job ID.

**Sidecar Lifecycle:**
- Reference Run operations and UI transitions; remove resolved slice entries after validator PASS.

**Exit Criteria:**
- Runs list and Trigger Run match prototype and real creation/lifecycle flows pass direct backend proof.

### Task 8: Align Run Details And Pipeline Results

**Purpose:**
- match prototype Run Details hierarchy and wire tabs, console, results, exports, feedback, recovery to current contracts

**Specification Coverage:**
- `renderRunDetails`
- Run detail, stages, jobs, events, exports, CV versions, admin compatibility operations

**Required Skills:**
- `skill-test-driven-development`
- `skill-frontend-component-engineering`
- `skill-full-stack-integration`
- `skill-backend-verification`
- `ui-ux-pro-max`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/app.py:admin_run_detail` and `/runs/{run_id}` routes
- Inspect: `src/fitcv_cp/run_artifact_contracts.py`, `src/fitcv_cp/run_artifact_mirror.py`, `src/fitcv_cp/observability.py`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Modify: `src/fitcv_cp/templates/run_detail_tab_enriched.html`
- Modify: `src/fitcv_cp/templates/run_detail_tab_jobs_input.html`
- Modify: `src/fitcv_cp/templates/run_detail_tab_profile.html`
- Modify: `src/fitcv_cp/templates/_run_detail_snapshot_tab.html`
- Modify: `src/fitcv_cp/templates/_process_console.html`
- Modify: `src/fitcv_cp/templates/_jobs_input_sources.html`
- Modify: `src/fitcv_cp/templates/_cv_review_queue.html`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_run_artifact_contracts.py`, `tests/test_fitcv_cp/test_run_artifact_mirror.py`, `tests/test_fitcv_cp/test_observability_contract.py`, `docs/api.md`

**Dependencies:**
- Task 7 validator PASS

**Steps:**
- [ ] Lock prototype header, status/actions, section order, tabs, result table, details/drawers, console, downloads, default open state.
- [ ] Reuse existing detail partials where already aligned; remove duplicate local variants instead of creating new components.
- [ ] Use shared state renderer for initial detail, tab fetch, polling/refresh, retryable action, non-retryable failure, stale data, export failure.
- [ ] Keep last valid detail/results while refreshing; bound polling to terminal state and page visibility.
- [ ] Preserve URL/deep-link tab state and focus after partial replacement.
- [ ] Update resolved Run Details mapping in sidecar.
- [ ] Run fresh independent validator checkpoint.

**Verification:**
- [ ] `uv run pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_run_artifact_contracts.py tests/test_fitcv_cp/test_run_artifact_mirror.py tests/test_fitcv_cp/test_observability_contract.py tests/test_fitcv_cp/test_run_detail_output_availability.py -q -k "run_detail or run_jobs or run_events or cv_version or export or process_console"`
- Expected: detail projection, artifacts, events, results, exports, recovery, DOM contract tests pass.
- [ ] Playwright: isolated terminal run, drawers/tabs, console default state, interest action, selection, keyboard focus, desktop dark and 375px light; source/direct tests cover remaining contract state variants and failure paths.

**Backend Proof:**
- Direct boundary: Run detail, stages, jobs, events, export, CV history, applicable action endpoints.
- Failure: run/job/CV not found, unavailable output, invalid transition, dependency/artifact failure.
- State: action transitions and artifacts persist consistently; failed action preserves previous valid run state.
- Contract evidence: `docs/api.md`, `/openapi.json`, artifact contracts/tests.
- Trace: reconstruct one run from run ID through events, stage artifacts, job result, action result.

**Sidecar Lifecycle:**
- Keep only unresolved tab/action mappings; remove resolved entries after validator PASS.

**Exit Criteria:**
- Run Details and Pipeline Results match prototype across terminal/non-terminal states with direct backend proof.

**Historical Context — 2026-08-05 (not acceptance evidence):**
- Prior report recorded focused Run Details results: `81 passed, 369 deselected`; direct backend action boundary/failure/state subset: `5 passed`.
- Prior isolated runtime on `127.0.0.1:8766` returned `200` with a temporary migrated database; port `8765` remained untouched.
- Prior Playwright report recorded no visible lifecycle actions, result Language/stars/Clear/Bookmark controls, no Marks/Why transport details, default-closed Console, selection state, interest action, visible keyboard focus, light/dark themes, 375px no-overflow, and zero console errors.
- This evidence predates restored sequential dependencies. Task 8 is pending until Tasks 1–7 complete and Task 8 produces fresh required proof plus a fresh validator result.

### Task 9: Align Scans

**Purpose:**
- match prototype managed Scan list/create/detail flows and keep scan state machine as backend owner

**Specification Coverage:**
- `renderScansPage`, `renderScanCompanyPicker`, `renderScanDetails`
- managed Scan specification and `scan_contracts.py`

**Required Skills:**
- `skill-test-driven-development`
- `skill-frontend-component-engineering`
- `skill-full-stack-integration`
- `skill-backend-verification`
- `ui-ux-pro-max`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/scan_contracts.py`, `src/fitcv_cp/scan_worker.py`
- Inspect: `src/fitcv_cp/app.py` Scan routes/admin routes
- Inspect: `src/fitcv_cp/store.py`, `src/fitcv_cp/sqlite_store.py`
- Modify: `src/fitcv_cp/templates/scans_list.html`, `src/fitcv_cp/templates/scan_detail.html`
- Reuse: `src/fitcv_cp/templates/_process_console.html`
- Modify: `tests/test_fitcv_cp/test_app.py`, `tests/test_fitcv_cp/test_scan_contracts.py`
- Modify only for proven worker defect: `tests/test_fitcv_cp/test_scan_worker.py`
- Verify: `docs/superpowers/specs/2026-08-01-19-49-fitcv-managed-scan-lifecycle-spec.md`, `/openapi.json`

**Dependencies:**
- Task 8 validator PASS

**Steps:**
- [ ] Freeze prototype list tabs/table/dialogs, company picker, detail sections, output views, actions, default open state.
- [ ] Bind create, list, detail, events, jobs, output, cancel, run-again, archive/unarchive, delete preview to existing contracts.
- [ ] Derive visible actions only from server capabilities; do not duplicate transition rules in template JavaScript.
- [ ] Use shared async states for empty/loading/pending/error/integrity-invalid, stale revision, retry, terminal success.
- [ ] Preserve last valid detail during polling and stop polling at terminal state or page invisibility.
- [ ] Update resolved Scan entry in sidecar.
- [ ] Run fresh independent validator checkpoint.

**Verification:**
- [ ] `uv run pytest tests/test_fitcv_cp/test_scan_contracts.py tests/test_fitcv_cp/test_scan_worker.py tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_app.py -q -k "scan"`
- Expected: normalization, validation, capabilities, idempotency, lifecycle, worker, persistence, output, DOM tests pass.
- [ ] Playwright: empty/list tabs, New Scan dialog and focus, keyboard tab navigation, 375px dark, no overflow, and zero console errors; source/direct tests cover create, pending, succeeded, failed, integrity-invalid, lifecycle, output, idempotency, and persistence.

**Backend Proof:**
- Direct boundary: all `/scans` operations.
- Failure: empty company selection, invalid transition, stale revision, worker/source dependency failure, invalid output integrity.
- State: idempotent create, persisted events/jobs/output, lifecycle mutation; failed transition leaves revision unchanged.
- Contract evidence: `/openapi.json`, `scan_contracts.py`, managed Scan spec/tests.
- Trace: reconstruct one Scan through scan ID, events, jobs, output checksum.

**Sidecar Lifecycle:**
- Reference Scan operations/capabilities; remove resolved entries after validator PASS.

**Exit Criteria:**
- Scan flows match prototype and backend state/capability truth remains single owner.

**Historical Context — 2026-08-05 (not acceptance evidence):**
- Prior report recorded focused Scan results: `49 passed, 530 deselected`; direct route/contract/failure/state/worker/persistence subset: `19 passed`.
- Prior Playwright report covered isolated runtime on `127.0.0.1:8766`; port `8765` remained untouched.
- This evidence predates restored sequential dependencies. Task 9 is pending until Tasks 1–8 complete and Task 9 produces fresh required proof plus a fresh validator result.

### Task 10: Complete Candidate Profile Recovery Integration

**Purpose:**
- preserve approved Candidate Profile UI exactly and add only missing real loading, retry, non-retryable, stale, resume behavior

**Specification Coverage:**
- `renderCandidateProfilesPage`, `renderCreationUpload`, `renderCreationReview`, `renderCreationConfirm`, `renderProfileDetailsPage`
- canonical Candidate Profile specification and existing integration sidecar

**Required Skills:**
- `skill-test-driven-development`
- `skill-frontend-component-engineering`
- `skill-full-stack-integration`
- `skill-backend-verification`
- `ui-ux-pro-max`

**Files And Symbols:**
- Inspect: `docs/superpowers/specs/2026-08-01-23-49-canonical-candidate-uniform-evidence-projection-spec.md`
- Inspect: `src/fitcv/candidate.py` executable field registry
- Inspect: `src/fitcv_cp/models.py` Candidate Profile request/response models
- Inspect: `src/fitcv_cp/candidate_profile_service.py`
- Inspect: `src/fitcv_cp/app.py` Candidate Profile routes/admin routes
- Inspect: `src/fitcv_cp/store.py`, `src/fitcv_cp/sqlite_store.py`
- Modify only where state wiring is missing: `src/fitcv_cp/templates/candidate_profiles.html`, `src/fitcv_cp/templates/candidate_profile_creation.html`, `src/fitcv_cp/templates/candidate_profile_detail.html`, `src/fitcv_cp/templates/candidate_profile_sections.html`
- Modify: `tests/test_candidate_profile_template_contract.py`
- Modify: `tests/test_fitcv_cp/test_candidate_profile_service.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_store.py`, `tests/test_fitcv_cp/test_sqlite_store.py`, `/openapi.json`

**Dependencies:**
- Task 9 validator PASS
- existing approved Candidate Profile parity tests green before edits

**Steps:**
- [ ] Run existing Candidate Profile parity tests before editing; stop and report if approved structures already fail.
- [ ] Add failing tests only for missing skeleton, retryable error, non-retryable recovery action, stale revision reconciliation, resume, duplicate confirmation states.
- [ ] Reuse confirmed baseline, derived claim, evidence, confirmation, detail structures; do not rename classes, reorder actions, or add traceability UI absent from prototype.
- [ ] Bind recovery controls to server capabilities and canonical attempt/profile resources; confirmation/detail render same server-owned canonical resource.
- [ ] Prove MD, DOCX, YAML staged processing, review CAS, retry resume, idempotent confirmation, persisted revision, archive/restore, Run selection.
- [ ] Bind frozen archived `Delete Profile` to idempotent hard-delete API: archived succeeded profiles with no Run profile or profile-revision reference only; deletion removes linked creation artifacts.
- [ ] Bind frozen `Undo regeneration` to idempotent server restore of retained pre-regeneration review snapshot; require re-approval after downstream invalidation and render only when `undo_regeneration` capability is true.
- [ ] Remove resolved Candidate Profile mappings from sidecar.
- [ ] Run fresh independent validator checkpoint.

**Verification:**
- [ ] `uv run pytest tests/test_candidate_profile_template_contract.py tests/test_candidate.py tests/test_candidate_profile_ingest.py tests/test_fitcv_cp/test_candidate_profile_service.py tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_app.py -q -k "candidate_profile or candidate_profiles"`
- Expected: existing parity remains green; staged lifecycle and recovery tests pass.
- [ ] Playwright: list/upload/baseline/derived/confirmation/detail, MD/DOCX/YAML, multiple entries, source dialogs, per-field/all regeneration, stale conflict, retryable/non-retryable failure, duplicate confirm, archive/restore, both viewports/themes, keyboard/focus.

**Backend Proof:**
- Direct boundary: field schema, attempt creation/polling, source, baseline/derived patch/regenerate/approve, confirm/retry, profile detail/list/lifecycle routes.
- Failure: unsafe/unsupported/corrupt upload, validation, stale revision, dependency/LLM failure, non-retryable failure, duplicate confirm.
- State: deterministic work preserved on LLM failure; retry resumes correct stage; confirmation is idempotent and persists one immutable profile revision; archive/restore is symmetric.
- Contract evidence: Candidate Profile spec, Pydantic models, `/openapi.json`, route/service/store tests.
- Trace: attempt ID, source block IDs, revision/fingerprint, profile ID, Run selection.

**Sidecar Lifecycle:**
- Keep only unresolved Candidate Profile operation/state mappings. Final deletion remains blocked on explicit user disposition even if slice passes.

**Exit Criteria:**
- approved UI is unchanged except proven recovery states; complete staged backend flow passes direct and browser proof.
- Candidate Profile delete and regeneration undo use server-owned transport; sidecar records resolved mapping and behavior.

**Historical Context — pre-reset implementation work (not acceptance evidence):**
- Existing delete and undo behavior is retained as implementation context only. Re-run both steps, all Task 10 proof, and a fresh validator after Task 9 completes.

### Task 11: Align Bookmarks

**Purpose:**
- match prototype Bookmarks hierarchy and make list, selection, removal, export use canonical errors and selection contracts

**Specification Coverage:**
- `renderBookmarksPage`
- Bookmark collection, selection, remove, export-preview, export routes

**Required Skills:**
- `skill-test-driven-development`
- `skill-full-stack-integration`
- `skill-backend-verification`
- `ui-ux-pro-max`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/app.py:get_bookmarks`, `remove_bookmark_selection`, `preview_bookmark_export`, `export_bookmark_selection`, canonical bookmark setters
- Inspect: `src/fitcv_cp/store.py` bookmark protocol/delegates
- Inspect: `src/fitcv_cp/sqlite_store.py` bookmark queries/mutations
- Modify: `src/fitcv_cp/templates/bookmarks.html`
- Modify: `tests/test_fitcv_cp/test_app.py`, `tests/test_fitcv_cp/test_store.py`, `tests/test_fitcv_cp/test_sqlite_store.py`
- Verify: `/openapi.json` Bookmark operations

**Dependencies:**
- Task 10 validator PASS

**Steps:**
- [ ] Lock prototype page head, filters, table, selection bar, details, empty state, dialogs, action order.
- [ ] Preserve URL-owned filter/sort/page state and selected intersection rules.
- [ ] Route export through `fitcvApiRequest` or same canonical error decoder; remove generic `Export failed` collapse.
- [ ] Use shared pending/error/retry/stale renderer for load, remove, preview, export; preserve selected rows after retryable failure.
- [ ] Remove resolved Bookmark entries from sidecar.
- [ ] Run fresh independent validator checkpoint.

**Verification:**
- [ ] `uv run pytest tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_app.py -q -k "bookmark"`
- Expected: query/selection intersection, removal, preview/export, persistence, errors, DOM tests pass.
- [ ] Playwright: empty/list/filter/select/remove/export-preview/export failure and success, keyboard, both viewports/themes.

**Backend Proof:**
- Direct boundary: Bookmark list, remove, export preview, export.
- Failure: invalid selection, missing bookmark, stale filtered selection, export serialization/dependency failure.
- State: removal affects only filtered selected intersection; failed export does not change bookmarks.
- Contract evidence: Pydantic envelopes, `/openapi.json`, store/route tests.

**Sidecar Lifecycle:**
- Reference Bookmark operations and selection state only; remove slice entries after validator PASS.

**Exit Criteria:**
- Bookmarks matches prototype and canonical error/selection behavior is visible and proven.

### Task 12: Align Synonyms

**Purpose:**
- match prototype Synonyms list/detail/editor flows and close uncaught async failures without duplicating policy rules

**Specification Coverage:**
- `renderSynonymsPage`, `renderSynonymDetails`
- synonym policy, suggestions, actions, processing log, backup operations

**Required Skills:**
- `skill-test-driven-development`
- `skill-frontend-component-engineering`
- `skill-full-stack-integration`
- `skill-backend-verification`
- `ui-ux-pro-max`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/app.py` Synonym routes/action helpers
- Inspect: `src/fitcv_cp/synonym_policy_io.py`, `src/fitcv_cp/synonym_proposals.py`
- Inspect: `src/fitcv_cp/store.py`, `src/fitcv_cp/sqlite_store.py`
- Modify: `src/fitcv_cp/templates/synonyms.html`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_synonym_global_policy_io.py`
- Modify: `tests/test_fitcv_cp/test_synonym_promote_preview_field_aware.py`
- Modify: `tests/test_fitcv_cp/test_synonym_promote_commit_field_aware.py`
- Verify: `tests/test_fitcv_cp/test_sqlite_store.py`, `/openapi.json`

**Dependencies:**
- Task 11 validator PASS

**Steps:**
- [ ] Lock prototype tabs, editor, issue presentation, suggestion table, selection actions, details dialog, processing log, backup actions, defaults.
- [ ] Add catches to every async operation and route all failures through shared state renderer; preserve server payload issues for editor validation.
- [ ] Keep policy revision and active bundle revision as backend truth; do not duplicate transition or promotion rules in JavaScript.
- [ ] Preserve selection/editor content after retryable failures and return focus from dialogs.
- [ ] Remove resolved Synonym entries from sidecar.
- [ ] Run fresh independent validator checkpoint.

**Verification:**
- [ ] `uv run pytest tests/test_fitcv_cp/test_synonym_global_policy_io.py tests/test_fitcv_cp/test_synonym_promote_preview_field_aware.py tests/test_fitcv_cp/test_synonym_promote_commit_field_aware.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_app.py -q -k "synonym"`
- Expected: parse/compile, revision conflict, promotion, actions, backup, persistence, error, DOM tests pass.
- [ ] Playwright: each synonym type, edit/save validation, suggestion detail, approve/decline/clear, processing empty/list, backup import failure/success, keyboard, both viewports/themes.

**Backend Proof:**
- Direct boundary: synonym policies, suggestions/detail/actions, processing runs, backup export/import.
- Failure: editor validation, stale draft/active revision, missing suggestion, invalid action, unsafe backup, provider/triage dependency failure where used.
- State: failed policy/action/import leaves policy and suggestions consistent; idempotency keys prevent duplicate effects.
- Contract evidence: Pydantic envelopes, `/openapi.json`, policy/proposal/store tests.
- Trace: suggestion ID through source Run, action, policy revision, processing run.

**Sidecar Lifecycle:**
- Reference Synonym operation/state mappings; remove resolved entries after validator PASS.

**Exit Criteria:**
- Synonyms matches prototype and no async operation fails silently or uncaught.

### Task 13: Align Preference Optimization

**Purpose:**
- match prototype Preference Optimization list/detail controls and finish real settings/policy lifecycle integration

**Specification Coverage:**
- `renderPreferenceOptimizationPage`, `renderOptimizationDetailsPage`
- approved Preference Optimization specification and current admin operations

**Required Skills:**
- `skill-test-driven-development`
- `skill-frontend-component-engineering`
- `skill-full-stack-integration`
- `skill-backend-verification`
- `ui-ux-pro-max`

**Files And Symbols:**
- Inspect: `docs/superpowers/specs/2026-07-23-12-31-fitcv-preference-optimization-frontend-backend-integration-spec.md`
- Inspect: `src/fitcv_cp/app.py` `admin_optimization*` handlers
- Inspect: `src/fitcv_cp/optimization_service.py`, `src/fitcv/inverse_optimization.py`
- Inspect: `src/fitcv_cp/settings_store.py`, `src/fitcv_cp/store.py`, `src/fitcv_cp/sqlite_store.py`
- Modify: `src/fitcv_cp/templates/optimization.html`
- Modify: `tests/test_fitcv_cp/test_optimization_page.py`
- Modify only for proven backend defect: `tests/test_inverse_optimization.py`, `tests/test_fitcv_cp/test_sqlite_store.py`, `tests/test_fitcv_cp/test_app.py`

**Dependencies:**
- Task 12 validator PASS

**Steps:**
- [ ] Lock prototype page/detail hierarchy, section order, default open state, controls, dialogs, notices, tables, process console, action order.
- [ ] Reuse already-aligned collapsible sections/process console; remove duplicate style/markup variants instead of rebuilding.
- [ ] Preserve server-rendered PRG, CAS tokens, ranking mode, personalization strength, candidate, active policy, rollback, run lifecycle ownership.
- [ ] Use shared states for pending submission, validation/conflict notice, empty evidence, dependency failure, retry, success while retaining valid server data.
- [ ] Remove resolved Optimization entries from sidecar.
- [ ] Run fresh independent validator checkpoint.

**Verification:**
- [ ] `uv run pytest tests/test_fitcv_cp/test_optimization_page.py tests/test_inverse_optimization.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_app.py -q -k "optimization or ranking_mode or personalization_strength"`
- Expected: settings projection, PRG, CAS, candidate/policy lifecycle, persistence, empty states, responsive contract, detail tests pass.
- [ ] Playwright: baseline/personalized modes, no evidence, candidate creation, activation/rejection, run detail, inactivation confirmation, remove, rollback, failures, keyboard, both viewports/themes.

**Backend Proof:**
- Direct boundary: current `admin_optimization*` HTTP handlers and underlying service/store methods.
- Failure: insufficient evidence, stale compare tokens, invalid mode/strength, active-policy guard, hidden/missing run, dependency failure.
- State: accepted candidate, activation/inactivation/remove/rollback persist atomically; failed operation leaves active policy unchanged.
- Contract evidence: approved Optimization spec, route source/tests, settings schema/store tests. If routes become OpenAPI operations, verify canonical `/openapi.json`; do not create parallel schema.
- Trace: public optimization run ID through policy snapshot, activation event, process console.

**Sidecar Lifecycle:**
- Remove resolved Optimization entries after validator PASS. If every slice is resolved, present explicit disposition for `docs/fitcv-settings-ui-prototype.integration.md`; do not delete without approval.

**Exit Criteria:**
- Preference Optimization matches prototype and all visible lifecycle actions have direct state and failure proof.

## Verification

Final verification starts only after all 13 independent validator checkpoints pass.

- `git hash-object docs/fitcv-settings-ui-prototype.html`
  - Expected: `989af611bd7767c148022c79ac00c5069d8a3956`
- `uv run pytest tests/test_fitcv_cp/test_local_routes.py tests/test_fitcv_cp/test_local_app.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_settings_store.py tests/test_fitcv_cp/test_queue.py tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_run_artifact_contracts.py tests/test_fitcv_cp/test_run_artifact_mirror.py tests/test_fitcv_cp/test_observability_contract.py tests/test_fitcv_cp/test_scan_contracts.py tests/test_fitcv_cp/test_scan_worker.py tests/test_fitcv_cp/test_candidate_profile_service.py tests/test_fitcv_cp/test_optimization_page.py tests/test_fitcv_cp/test_synonym_global_policy_io.py tests/test_fitcv_cp/test_synonym_promote_preview_field_aware.py tests/test_fitcv_cp/test_synonym_promote_commit_field_aware.py tests/test_candidate_profile_template_contract.py tests/test_candidate.py tests/test_candidate_profile_ingest.py tests/test_inverse_optimization.py -q`
- `uv run python -m compileall -q src/fitcv_cp src/fitcv`
- Inspect `/openapi.json` from normal and packaged-local app factories; expected registered operations and local-only boundaries remain unchanged unless explicitly approved contract change updated source, tests, `docs/api.md`.
- Playwright full route matrix: `1440x900`, `375x812`, light/dark, keyboard/focus, reduced motion, long content, empty/loading/error/success, stale/retry, no horizontal overflow.
- Chrome DevTools final pass: no uncaught console errors, duplicate submissions, runaway polling, unexpected request shapes, layout shifts.
- `git diff --check`
- `git status --short`
  - Expected: only explicitly owned files changed; all pre-existing unknown/user files preserved.

## Completion Criteria

Plan is ready for completion verification when:

1. prototype hash remains exactly `989af611bd7767c148022c79ac00c5069d8a3956`;
2. `base.html` is sole runtime owner of shared CSS, shell, and async-state rendering; genuinely page-specific CSS remains local without duplicated shared selectors;
3. runtime navigation matches prototype, Prompt Management remains visible, Lifecycle has no page route or template, `/local/system` redirects to `/admin/system`, and `/local/lifecycle/status` remains shutdown-only;
4. every listed page matches prototype hierarchy, order, classes, actions, labels, button variants, default expanded state, responsive behavior, themes, keyboard/focus, applicable UI states;
5. already-parity-aligned components remain reused and unchanged unless failing validator identified exact drift;
6. no prototype sample value becomes transport field or backend rule;
7. every backend-consuming slice has fresh direct boundary, validation, state, failure, conflict/idempotency, dependency, contract, trace evidence by applicability;
8. all 13 fresh independent validator checkpoints report PASS;
9. sidecar contains only unresolved mappings and receives explicit final disposition before deletion;
10. no new frontend framework, CSS pipeline, client generator, duplicate schema, mock infrastructure, broad abstraction was added;
11. current uncommitted and unknown files remain preserved;
12. focused and final automated checks pass with fresh output;
13. deviations, substitutions, blockers, deferrals are recorded in this plan.

Only `skill-verification-before-completion` may mark plan `completed` after fresh proof. Branch/worktree disposition remains separate and requires explicit authorization.
