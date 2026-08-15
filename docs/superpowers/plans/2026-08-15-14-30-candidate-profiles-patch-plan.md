---
layer: change
artifact_type: plan
status: active
template_id: implementation-plan
name: candidate-profiles-prototype-integration-pipeline-compatibility
parent_spec: none
coordination:
  controller: codex
  executor: dcode-project
  target_branch: main
  base_ref: 6ac172f920ea7d2ee03f2050ea702fd092516773
  mode: inline_sequential
  task_state_owner: codex
  runtime_state: ephemeral
  tasks:
    - id: task-1-freeze-candidate-profile-contracts
      depends_on: []
      execution_mode: inline_sequential
      dcode_role: normal
      allowed_paths:
        - docs/fitcv-settings-ui-prototype.integration.md
        - docs/api.md
        - tests/test_fitcv_cp/candidate_profile_fixtures.py
        - tests/test_candidate_profile_ingest.py
        - tests/test_fitcv_cp/test_app.py
    - id: task-2-canonical-profile-lifecycle-api
      depends_on: [task-1-freeze-candidate-profile-contracts]
      execution_mode: inline_sequential
      dcode_role: high
      allowed_paths:
        - src/fitcv/candidate.py
        - src/fitcv_cp/candidate_profile_service.py
        - src/fitcv_cp/candidate_profile_seeds.py
        - src/fitcv_cp/sqlite_store.py
        - src/fitcv_cp/app.py
        - data/candidate_profile.template.yaml
        - tests/test_candidate_profile_ingest.py
        - tests/test_fitcv_cp/test_candidate_profile_service.py
        - tests/test_fitcv_cp/test_sqlite_store.py
        - tests/test_fitcv_cp/test_app.py
    - id: task-3-job-pipeline-snapshot-contract
      depends_on: [task-2-canonical-profile-lifecycle-api]
      execution_mode: inline_sequential
      dcode_role: high
      allowed_paths:
        - src/fitcv_cp/app.py
        - src/fitcv_cp/sqlite_store.py
        - src/fitcv_cp/worker_job.py
        - src/fitcv_cp/worker_run_support.py
        - src/fitcv_cp/run_artifact_contracts.py
        - src/fitcv_cp/run_artifact_mirror.py
        - src/fitcv_cp/run_lifecycle.py
        - tests/test_fitcv_cp/test_app.py
        - tests/test_fitcv_cp/test_worker_job.py
        - tests/test_fitcv_cp/test_run_lifecycle.py
        - tests/test_pipeline_checkpoint_contract.py
        - tests/test_pipeline_stage_resume_parity.py
    - id: task-4-candidate-profile-ui-contract
      depends_on: [task-3-job-pipeline-snapshot-contract]
      execution_mode: inline_sequential
      dcode_role: normal
      allowed_paths:
        - src/fitcv_cp/templates/candidate_profiles.html
        - src/fitcv_cp/templates/candidate_profile_creation.html
        - src/fitcv_cp/templates/candidate_profile_detail.html
        - src/fitcv_cp/templates/candidate_profile_sections.html
        - src/fitcv_cp/templates/run_detail.html
        - src/fitcv_cp/templates/run_detail_tab_profile.html
        - src/fitcv_cp/templates/_run_detail_snapshot_tab.html
        - tests/test_candidate_profile_template_contract.py
        - tests/test_fitcv_cp/test_app.py
        - tests/test_fitcv_cp/test_local_routes.py
    - id: task-5-settings-output-propagation
      depends_on: [task-4-candidate-profile-ui-contract]
      execution_mode: inline_sequential
      dcode_role: normal
      allowed_paths:
        - src/fitcv_cp/settings_schema.py
        - src/fitcv_cp/settings_store.py
        - src/fitcv_cp/retry_settings.py
        - src/fitcv_cp/templates/settings.html
        - tests/test_fitcv_cp/test_settings_schema.py
        - tests/test_fitcv_cp/test_settings_store.py
        - tests/test_fitcv_cp/test_settings_store_sqlite.py
        - tests/test_fitcv_cp/test_retry_settings.py
    - id: task-6-isolated-end-to-end-verification
      depends_on: [task-4-candidate-profile-ui-contract, task-5-settings-output-propagation]
      execution_mode: inline_sequential
      dcode_role: xhigh
      allowed_paths:
        - data/2026-06-24-Munich_Electrification-CV.md
        - data/2026-06-27-Beiersdorf-CV.md
        - tests/test_candidate_profile_ingest.py
        - tests/test_candidate_profile_template_contract.py
        - tests/test_fitcv_cp/test_app.py
        - tests/test_fitcv_cp/test_candidate_profile_service.py
        - tests/test_fitcv_cp/test_local_app.py
        - tests/test_fitcv_cp/test_local_routes.py
        - tests/test_fitcv_cp/test_run_lifecycle.py
        - tests/test_fitcv_cp/test_settings_schema.py
        - tests/test_fitcv_cp/test_settings_store.py
        - tests/test_fitcv_cp/test_settings_store_sqlite.py
        - tests/test_fitcv_cp/test_worker_job.py
        - tests/test_pipeline_checkpoint_contract.py
        - tests/test_pipeline_stage_resume_parity.py
targets:
  - docs/fitcv-settings-ui-prototype.integration.md
  - docs/api.md
  - src/fitcv/candidate.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/candidate_profile_service.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/worker_run_support.py
  - src/fitcv_cp/run_artifact_contracts.py
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/settings_store.py
  - src/fitcv_cp/templates/candidate_profiles.html
  - src/fitcv_cp/templates/candidate_profile_creation.html
  - src/fitcv_cp/templates/candidate_profile_detail.html
  - src/fitcv_cp/templates/candidate_profile_sections.html
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - tests/test_fitcv_cp/test_worker_job.py
related_features:
  - candidate-profiles
  - job-pipeline
---

# Implementation Plan: Candidate Profiles Prototype, Integration, and Pipeline Compatibility

## Goal

Bring Candidate Profiles into verified product parity with the Candidate Profiles portions of `docs/fitcv-settings-ui-prototype.html`, complete its frontend/backend contracts, and preserve immutable, canonical Candidate Profile consumption by Job Pipeline runs.

## Implementation Outcomes

### Canonical Candidate Profile lifecycle

Confirmed Candidate Profiles use canonical V2 runtime convergence, return actionable review validation errors, support immutable revision updates, and enforce create, view, update, archive, restore, and delete-after-archive rules with CAS and idempotency.

### Immutable Job Pipeline input

Every Candidate Profile-backed run stores one authoritative `run_inputs` snapshot with profile identity, revision, canonical payload, normalized schema version, and checksum. Workers, retries, checkpoints, artifacts, and run detail read that stored snapshot rather than mutable current-profile data.

### Prototype-aligned usable UI

Existing Candidate Profile templates, not generic Pipeline settings, expose prototype-equivalent profile creation, staged review, Active/Archived lifecycle, traceability, related runs, and recoverable async states.

### Fresh proof

Focused direct backend, contract, browser, and isolated live-like checks cover both supplied CVs without modifying user files or user runtime data.

## Execution Approach

- Mode: `inline_sequential`
- Required skills: `skill-deepagents-executing-plans`, `skill-executing-plans`, `skill-backend-verification`, `skill-full-stack-integration`, `ui-ux-pro-max`, `skill-test-driven-development`, `skill-verification-before-completion`
- Isolation: execute one bounded task at a time through `dcode-project --role <low|normal|high|xhigh> --handoff-file <validated-file>` against exact native repository root; use temporary SQLite and artifact roots for integration probes
- Commit policy: Codex lead creates checkpoint commits only after task proof is accepted and the task ledger is updated in the same commit
- Parallel ownership: none; same-workspace writers remain sequential; DeepAgents cannot edit coordination state, commit, push, or spawn nested agents
- Sequential fallback: Tasks 1 through 6 remain one deterministic dependency chain; no task may advance while an earlier task lacks accepted proof

## DeepAgents Handoff Contract

- Codex is sole coordination controller, plan writer, MCP authority, Git authority, and acceptance owner.
- Each handoff contains task ID, plan name, target branch, base ref, current `HEAD`, clean/dirty status, dependency result, exact `allowed_paths`, required proof commands, and acceptance criteria.
- Handoffs use validated `codex.mcp.handoff.v1` facts through a handoff file. Never pass raw `--stdin`, shell-piped task text, secrets, runtime state, or database paths.
- DeepAgents reads and writes only named source, test, and text files. It must not read databases, binaries, archives, runtime artifacts, `.deepagents/`, or credentials.
- Every task result starts with `PASS`, `FAIL`, or `BLOCKED`, then lists changed files, `path:line` evidence, commands and results, remaining risks, and unresolved blockers.
- DeepAgents output is a claim. Codex reconciles it against Plan plus Git, rejects out-of-scope changes, accepts proof, updates the ledger, and only then selects the next task.

## Coordination State

- Coordination owner: `Codex lead controller`
- Branch: `main`
- Base commit: `93baf43b6f522518281b1e21d8f09cff352d7c14`
- Plan status: `active`
- Active task: `task-6-isolated-end-to-end-verification`
- Next eligible task: `none` after Task 6 acceptance
- Last accepted checkpoint: `93baf43b6f522518281b1e21d8f09cff352d7c14`
- Task 1 accepted proof: `PASS` — `465 passed in 78.14s` from `tests/test_candidate_profile_ingest.py` and `tests/test_fitcv_cp/test_app.py`; compile and diff checks passed.
- Task 2 accepted proof: `PASS` — `592 passed` from Candidate Profile ingest, service, store, and app suites; clean Git diff.
- Task 3 accepted proof: `PASS` — four regressions passed independently; full Task 3 suite passed `567 tests`; `git diff --check` passed.
- Task 4 accepted proof: `PASS` — template, app, and local route suites passed `489 tests`; clean Git diff.
- Task 5 accepted proof: `PASS` — settings suites passed `218 passed, 1 skipped`; compile and diff checks passed.
- Runtime state: `ephemeral`; never use DeepAgents or Codex session state for recovery
- Workspace rule: same-workspace writers execute sequentially

## Task Ledger

| Task ID | Depends on | Status | Executor | Proof owner |
| --- | --- | --- | --- | --- |
| `task-1-freeze-candidate-profile-contracts` | none | completed | `dcode-project --role normal` | Codex |
| `task-2-canonical-profile-lifecycle-api` | task 1 | completed | `dcode-project --role high` | Codex |
| `task-3-job-pipeline-snapshot-contract` | task 2 | completed | `dcode-project --role high` | Codex |
| `task-4-candidate-profile-ui-contract` | task 3 | completed | `dcode-project --role normal` | Codex |
| `task-5-settings-output-propagation` | task 4 | completed | `dcode-project --role normal` | Codex |
| `task-6-isolated-end-to-end-verification` | tasks 4 and 5 | active | `dcode-project --role xhigh` | Codex |

## Constraints and Decisions

- Treat `docs/fitcv-settings-ui-prototype.html` as product behavior and visual reference. Do not clone its standalone implementation or force Candidate Profiles through `src/fitcv_cp/templates/settings.html`.
- Reuse `converge_candidate_profile_for_runtime()` in `src/fitcv/candidate.py`; do not introduce another V1/V2 adapter.
- Confirmed-profile update means immutable successor revision, never mutation of a confirmed revision. Existing runs remain bound to their original snapshot.
- Extend existing `run_inputs` storage; do not add a parallel snapshot envelope or second source of truth.
- Preserve legacy null or `{}` snapshots as explicitly labeled read-only historical records. New Candidate Profile-backed runs fail closed when selected profile is missing, malformed, stale, or disallowed by lifecycle policy.
- Current live verification is blocked. On August 15, 2026, no FitCV service was running. CV hashes were unchanged: Munich `FC5C96B2C06263D726D645B187374999E0AEC9D6F0413AA98859C814601DB85A`; Beiersdorf `E4C9B089B8E5075B3BC2DF513FBCC2FE07A7FEF31439E12AF0ED11308726F27A`.

## Task Breakdown

### Task 1: Freeze Candidate Profile contracts and compatibility policy

**Coordination ID:** `task-1-freeze-candidate-profile-contracts`

**Purpose:** Establish executable acceptance contracts before changing route, schema, or UI behavior.

**Specification Coverage:** Canonical format, immutable update, lifecycle policy, source-block contract, all run-creation entrypoints, and prototype-to-server-template mapping.

**Files:**
- `docs/fitcv-settings-ui-prototype.integration.md`
- `docs/api.md`
- `tests/test_fitcv_cp/candidate_profile_fixtures.py`
- `tests/test_candidate_profile_ingest.py`
- `tests/test_fitcv_cp/test_app.py`

**Changes:**
1. Add Candidate Profile parity matrix to integration sidecar: creation fields, accepted source formats, staged draft/review/resume, Active/Archived views, detail traceability, lifecycle controls, related runs, and each async state.
2. Document one source-block request/response route. Use existing handler behavior as canonical unless its response cannot retrieve requested source-block data; change handler and client together, never add accidental aliases.
3. Define immutable successor-revision update contract: input revision CAS, validation, checksum, active/archived rules, historical snapshot preservation, and response shape.
4. Inventory JSON trigger, managed multipart trigger, and `/admin/upload-trigger`. Require active persisted profile for Candidate Profile-selected runs; retain legacy default-config behavior only when explicitly labeled, documented, and tested.
5. Add shared fixture expectations for canonical V2 profile, legacy V1 profile, invalid profile, active/archived profile, immutable run snapshot, and legacy empty snapshot.

**Verification:** Route/fixture tests prove contract fields and unsupported lifecycle transitions before store or UI edits.

**Acceptance:** No later task invents a second V1/V2 adapter, snapshot record, source-block route alias, or confirmed-profile overwrite path.

### Task 2: Repair canonical schema, review validation, lifecycle persistence, and API

**Coordination ID:** `task-2-canonical-profile-lifecycle-api`

**Purpose:** Make profile resource behavior authoritative before Pipeline or UI wiring.

**Files:**
- `src/fitcv/candidate.py`
- `src/fitcv_cp/candidate_profile_service.py`
- `src/fitcv_cp/candidate_profile_seeds.py`
- `src/fitcv_cp/sqlite_store.py`
- `src/fitcv_cp/app.py`
- `data/candidate_profile.template.yaml`
- `tests/test_candidate_profile_ingest.py`
- `tests/test_fitcv_cp/test_candidate_profile_service.py`
- `tests/test_fitcv_cp/test_sqlite_store.py`
- `tests/test_fitcv_cp/test_app.py`

**Changes:**
1. Reuse `converge_candidate_profile_for_runtime()` for V1 adaptation and V2 pass-through. Add regression tests proving canonical `search_preferences` reaches runtime/persistence and V1 compatibility remains read-safe.
2. Validate assembled review resources and review mutations with `validate_candidate_profile_v2()`. Return stable field/path errors instead of literal empty `field_errors`; reject malformed scalar/container shapes and invalid patched documents.
3. Add immutable confirmed-profile successor revision creation. Require expected revision, canonical validation, source/checksum recalculation, and active/archived lifecycle checks; never rewrite prior confirmed revision rows.
4. Preserve archive and restore CAS behavior. Test restore success. Enforce delete only for succeeded, archived, CAS-current, unreferenced revisions; cover active, failed, stale, referenced, idempotent replay, and idempotency-key payload-conflict cases.
5. Keep seed-manifest and profile-schema revisions separate. Add a failing regression before any repair migration; do not schedule speculative data migration.
6. Update API documentation and route tests for source blocks, immutable revision update, review errors, archive, restore, and delete contracts.

**Verification:**
```powershell
py -m pytest -q tests/test_candidate_profile_ingest.py tests/test_fitcv_cp/test_candidate_profile_service.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_app.py
```

**Acceptance:** Valid profiles serialize as canonical V2, invalid review data returns field-specific errors, lifecycle operations survive concurrent retries correctly, and previous confirmed revisions remain immutable.

### Task 3: Make existing `run_inputs` snapshot contract authoritative

**Coordination ID:** `task-3-job-pipeline-snapshot-contract`

**Purpose:** Preserve downstream Job Pipeline compatibility without mutable-profile drift.

**Files:**
- `src/fitcv_cp/app.py`
- `src/fitcv_cp/sqlite_store.py`
- `src/fitcv_cp/worker_job.py`
- `src/fitcv_cp/worker_run_support.py`
- `src/fitcv_cp/run_artifact_contracts.py`
- `src/fitcv_cp/run_artifact_mirror.py`
- `src/fitcv_cp/run_lifecycle.py`
- `tests/test_fitcv_cp/test_app.py`
- `tests/test_fitcv_cp/test_worker_job.py`
- `tests/test_fitcv_cp/test_run_lifecycle.py`
- `tests/test_pipeline_checkpoint_contract.py`
- `tests/test_pipeline_stage_resume_parity.py`

**Changes:**
1. Extend existing `run_inputs` fields with normalized schema version and selected revision checksum/fingerprint alongside current profile identity, revision, name, and canonical JSON.
2. Reconcile all run creation routes from Task 1. Candidate Profile-selected runs validate and snapshot once before enqueue; default-config legacy routes retain explicit source metadata and contract tests.
3. Replace new-run silent `{}` profile fallback with explicit failure. Decode historical null/empty snapshots as legacy records with non-destructive UI messaging.
4. Preserve snapshot identity/payload through worker input, checkpoint/resume, whole-run retry, stage retry, artifact export, and terminal mirror.
5. Ensure run detail shows stored snapshot as truth. Current profile lookup may show comparison metadata only; it must not replace historical payload or lifecycle state.

**Verification:**
```powershell
py -m pytest -q tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_run_lifecycle.py tests/test_pipeline_checkpoint_contract.py tests/test_pipeline_stage_resume_parity.py
```

**Acceptance:** Updating, archiving, restoring, or deleting a later profile revision cannot alter an already-created run's worker input, retry input, checkpoint, exported artifact, or displayed snapshot.

### Task 4: Wire prototype-aligned Candidate Profile UI to stabilized contracts

**Coordination ID:** `task-4-candidate-profile-ui-contract`

**Purpose:** Complete end-user workflows after backend and Pipeline behavior are fixed.

**Files:**
- `src/fitcv_cp/templates/candidate_profiles.html`
- `src/fitcv_cp/templates/candidate_profile_creation.html`
- `src/fitcv_cp/templates/candidate_profile_detail.html`
- `src/fitcv_cp/templates/candidate_profile_sections.html`
- `src/fitcv_cp/templates/run_detail.html`
- `src/fitcv_cp/templates/run_detail_tab_profile.html`
- `src/fitcv_cp/templates/_run_detail_snapshot_tab.html`
- `tests/test_candidate_profile_template_contract.py`
- `tests/test_fitcv_cp/test_app.py`
- `tests/test_fitcv_cp/test_local_routes.py`

**Changes:**
1. Align Candidate Profile list, creation, detail, and lifecycle layout to prototype behavior: source upload/validation, Profile Name, staged processing, draft failure/resume, Active/Archived views, overview/source/traceability groups, and lifecycle availability.
2. Wire one source-block route and existing retry endpoint. Preserve expected revision, idempotency key, request lock, enqueue result, and stale-CAS recovery.
3. Add immutable revision-update, archive, restore, and delete controls only where capability/lifecycle allows them.
4. Replace inert related-run buttons with semantic canonical run-detail links. Cover related-run initial/loading/success/empty/pagination/error states.
5. Define initial/loading/success/empty/validation/error/stale-CAS/disabled states for source block, retry, revision update, archive, restore, delete, and related runs. Restore focus after dialogs/errors and prevent duplicate submissions.
6. Make run detail distinguish immutable trigger-time snapshot from current-profile comparison metadata and legacy missing-snapshot state.

**Verification:** Template contract tests plus browser-harness evidence for keyboard focus, desktop/mobile layout, supported theme, disabled states, and no duplicate request.

**Acceptance:** Every prototype-required Candidate Profile workflow maps to one server-backed control or explicit documented non-support state; no visible control silently fails.

### Task 5: Prove settings projection and profile-output propagation

**Coordination ID:** `task-5-settings-output-propagation`

**Purpose:** Prevent Candidate Profile settings UI from claiming effects absent from canonical generated profiles.

**Files:**
- `src/fitcv_cp/settings_schema.py`
- `src/fitcv_cp/settings_store.py`
- `src/fitcv_cp/retry_settings.py`
- `src/fitcv_cp/templates/settings.html`
- `tests/test_fitcv_cp/test_settings_schema.py`
- `tests/test_fitcv_cp/test_settings_store.py`
- `tests/test_fitcv_cp/test_settings_store_sqlite.py`
- `tests/test_fitcv_cp/test_retry_settings.py`

**Changes:**
1. Add Candidate Profile settings page-projection tests for editable, read-only, and hidden rows.
2. Test corrupt stored JSON, legacy/canonical duplicate rows, transaction rollback, stale revision conflict, retry coercion, and retry bounds.
3. Add integration proof that supported composition settings produce expected normalized profile and run-snapshot values. Remove unsupported UI expectation instead of adding unused configuration.

**Verification:**
```powershell
py -m pytest -q tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_settings_store.py tests/test_fitcv_cp/test_settings_store_sqlite.py tests/test_fitcv_cp/test_retry_settings.py
```

**Acceptance:** Displayed settings, persisted values, canonical profile output, and Job Pipeline snapshot agree across success, empty/default, invalid, stale, and rollback paths.

### Task 6: Run isolated end-to-end and live-like verification

**Coordination ID:** `task-6-isolated-end-to-end-verification`

**Purpose:** Prove whole workflow without writing user data or depending on current local runtime state.

**Files:** Existing test/browser harnesses only; do not persist artifacts under repository `data`, user runtime roots, or supplied CV paths.

**Changes:**
1. Configure temporary SQLite and artifact roots. Record paths, request IDs, response status, fixture hashes, and cleanup proof.
2. Exercise create, source-block inspect, failed retry, review/update, confirm, run selection, immutable snapshot inspection, archive, restore, and eligible delete.
3. Use both supplied CVs from `data/2026-06-24-Munich_Electrification-CV.md` and `data/2026-06-27-Beiersdorf-CV.md` as immutable inputs only. Hash before/after, retain clean Git diff except those two pre-existing untracked files, and delete temporary runtime data.
4. DeepAgents may run only native filesystem, `git`, and `py` proof available through `dcode-project`. It must return `BLOCKED` for unavailable browser, web, MCP, or live-service evidence; Codex controller owns any post-task browser proof and records it separately.

**Verification:** Run focused suites from Tasks 2-5, affected full suite, then hand off browser/live-like flow to Codex controller when DeepAgents lacks required capability. Record direct backend evidence, request IDs, fixture hashes, cleanup proof, and every `BLOCKED` capability.

**Acceptance:** Both CVs produce canonical profile output ready for selected Job Pipeline runs; failure paths leave no partial persisted state; user CV hashes and user runtime data remain unchanged.

## Completion Criteria

- Candidate Profile UI, API, persistence, settings, and Job Pipeline behavior satisfy one documented contract.
- Every lifecycle action has direct backend success/failure/state proof and frontend loading/empty/error/stale proof.
- Existing and historical run snapshots remain readable and immutable.
- No unproven schema migration, compatibility alias, duplicate adapter, or duplicate snapshot source of truth is introduced.
- Final verification records focused test commands, browser evidence, isolated live-like evidence, remaining blocker or `none`, and no unplanned file changes.
