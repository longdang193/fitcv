---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: fitcv-local-controller-ssot-and-safe-prompt-customization
parent_thread: workstream-operator-control-plane.fitcv-local-distribution-and-onboarding
parent_spec: docs/superpowers/specs/2026-07-17-10-02-fitcv-local-controller-ssot-and-safe-prompt-customization-spec.md
targets:
  - config/runtime/control_plane.yaml
  - config/runtime/prompts.yaml
  - src/fitcv/config.py
  - src/fitcv/runtime_routing.py
  - src/fitcv/prompts/registry.py
  - src/fitcv/prompts/renderer.py
  - src/fitcv/prompts/templates
  - src/fitcv/enrich.py
  - src/fitcv/ai_score.py
  - src/fitcv/cv_generator.py
  - src/fitcv/pipeline_stage_artifacts.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/local_storage.py
  - src/fitcv_cp/local_setup.py
  - src/fitcv_cp/local_routes.py
  - src/fitcv_cp/retry_settings.py
  - src/fitcv_cp/templates/local_onboarding.html
  - packaging/windows/fitcv-local.spec
  - scripts/smoke_fitcv_local.ps1
  - tests/test_config.py
  - tests/test_runtime_routing.py
  - tests/test_prompts.py
  - tests/test_enrich.py
  - tests/test_ai_score.py
  - tests/test_cv_generator.py
  - tests/test_fitcv_cp
  - tests/test_fitcv_local_packaging.py
  - docs/features/admin_control_plane_core/feature.source.yaml
  - docs/features/settings_system/feature.source.yaml
  - docs/features/cv_system/feature.source.yaml
  - docs/features/inspection_debugging/feature.source.yaml
  - docs/stages/enrich.source.yaml
  - docs/stages/ranking.source.yaml
  - docs/stages/cv_generation.source.yaml
  - docs/configuration.md
  - docs/setup.md
  - docs/usage.md
related_features:
  - admin_control_plane_core
  - settings_system
  - cv_system
  - inspection_debugging
  - run_lifecycle_controls
related_stages:
  - enrich
  - ranking
  - cv_generation
---

# FitCV Local Controller SSOT And Safe Prompt Customization Implementation Plan

## Goal

Implement one validated FitCV Local controller configuration path that keeps
packaged runtime defaults in canonical YAML, keeps supported identities in shared
code registries, migrates the legacy routing overlay without data loss, and lets
users add bounded task guidance without editing immutable prompt contracts.

Execution must reuse the existing local onboarding surface, existing prompt
renderer, existing structured-output validators, existing credential store, and
existing run-retry behavior. No new dependency, desktop framework, arbitrary
YAML editor, prompt marketplace, or per-LLM-request retry engine is added.

## Key Deliverables

### One controller ownership and resolution contract

`config/runtime/control_plane.yaml` owns provider, routing, timeout, and run-retry
defaults. `config/runtime/prompts.yaml` owns active prompt IDs. Shared typed
registries own supported provider, wire API, auth-mode, routing-part, and prompt
addendum identities. One effective-config resolver applies packaged defaults,
validated local overlay, then existing explicit per-run overrides. Runtime and UI
consumers stop declaring policy fallbacks such as timeout `120`, wire API
`responses`, retry defaults, or prompt IDs.

### One migration-safe user controller overlay

FitCV Local stores non-secret user configuration in versioned
`<data-root>/config/local_controller_overlay.yaml`. One reader/writer validates
allowed provider, routing, run-retry, and prompt-addendum sections. First use
atomically migrates supported values from `local_routing_overlay.yaml`; failed
migration leaves old data recoverable. Backup, restore, relocation, restart, and
readiness flows preserve or safely reject the new overlay.

### Safe prompt addenda with private provenance

Supported task prompts accept one bounded addendum inserted as literal text once
before immutable JSON/schema/output-contract instructions. Existing structured
response modes, parsers, validators, schemas, grounding rules, and semantic stage
rules remain authoritative. Runtime evidence stores only prompt identity,
customization status, normalized SHA-256, and character count; raw addenda stay
in the local overlay and explicit backups only.

### Existing UI and packaged runtime prove parity

The revisitable FitCV Local onboarding page exposes effective controller values,
source indicators, run-retry controls, per-task prompt addenda, validation errors,
and reset-to-default actions. Source and packaged verification prove the same
controller/prompt contract, prompt asset presence, privacy boundaries, structured
output rejection, default reset behavior, and unchanged Docker/server mode.

## Task/Wave Breakdown

### Task 1: Establish registries and overlay contract

**Purpose:**
- Define one supported-identity registry and one strict local controller overlay schema before changing consumers.

**Files:**
- Modify: `config/runtime/control_plane.yaml`
- Modify: `config/runtime/prompts.yaml`
- Modify: `src/fitcv/config.py`
- Modify: `src/fitcv_cp/local_storage.py`
- Modify: `src/fitcv_cp/local_setup.py`
- Verify: `tests/test_config.py`
- Verify: `tests/test_fitcv_cp/test_local_storage.py`
- Verify: `tests/test_fitcv_cp/test_local_setup.py`

**Preconditions:**
- Approved parent specification remains unchanged.
- Run `./scripts/get_gitnexus_freshness.ps1`; refresh stale graph before high-trust impact checks when possible.
- Run GitNexus upstream impact analysis for each edited function, class, or shared registry symbol; stop and warn before HIGH or CRITICAL edits.

**Steps:**
- [x] Add typed registries in `src/fitcv/config.py` for supported provider IDs, provider types, auth modes, wire APIs, routing parts, prompt-addendum task IDs, UI labels, and validation bounds.
- [x] Add missing canonical provider/retry fields to `config/runtime/control_plane.yaml` and `synonym_triage.recommendation.prompt_id` to `config/runtime/prompts.yaml`.
- [x] Define versioned `local_controller_overlay.yaml` validation that permits only `providers`, `model_routing.parts`, `fitcv_cp.retry`, and `prompts.additional_instructions`.
- [x] Reject every field outside the strict schema allowlist, incomplete provider/routes, non-positive timeouts, invalid retry values, non-string addenda, and normalized addenda above `4000` Unicode code points.
- [x] Normalize addenda by converting CRLF/CR to LF and stripping surrounding whitespace; whitespace-only values remove the key, hashes use normalized UTF-8 bytes, and character counts use normalized text.
- [x] Keep runtime default values out of registries; read them only from canonical YAML.
- [x] Replace routing-specific path naming in local storage structures with controller-overlay naming while retaining an explicit legacy path for migration only.

**Verification:**
- [x] `./.venv/Scripts/python.exe -m pytest tests/test_config.py tests/test_fitcv_cp/test_local_storage.py tests/test_fitcv_cp/test_local_setup.py -q`
- [x] Tests prove allowed identities are shared, arbitrary nested config is rejected, and credentials cannot enter overlay payloads.

**Exit Criteria:**
- Every configurable default has one YAML owner, every supported identity has one registry owner, and overlay shape has no escape hatch.

### Task 2: Migrate and preserve local controller data

**Purpose:**
- Activate the new overlay without losing existing routing choices or weakening local data lifecycle guarantees.

**Files:**
- Modify: `src/fitcv_cp/local_storage.py`
- Modify: `src/fitcv_cp/local_setup.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_local_storage.py`
- Verify: `tests/test_fitcv_cp/test_local_app.py`
- Verify: `tests/test_fitcv_cp/test_local_setup.py`

**Preconditions:**
- Task 1 complete.
- GitNexus upstream impact checks completed for storage activation, backup, restore, relocation, setup write, and startup symbols before edits.

**Steps:**
- [x] Add atomic write support for validated controller overlays using the existing local storage write pattern.
- [x] When the new overlay and retired legacy backup are absent but the exact legacy file exists, copy only validated `providers` and `model_routing` into the new versioned file.
- [x] Atomically write and revalidate the new file, then rename the legacy file to `local_routing_overlay.yaml.migrated.bak`; a valid new file always wins.
- [x] When both files exist after interrupted retirement, use the new file, retry the rename, and never reimport legacy values.
- [x] Include the new overlay in backup manifests, restore validation, relocation, storage inspection, and restart paths; keep credentials excluded.
- [x] Add injected-failure and restart tests for migration, backup, restore, and relocation.

**Verification:**
- [x] `./.venv/Scripts/python.exe -m pytest tests/test_fitcv_cp/test_local_storage.py tests/test_fitcv_cp/test_local_app.py tests/test_fitcv_cp/test_local_setup.py -q`
- [x] Migration tests prove atomic new-file replacement, interrupted-retirement recovery, idempotence, and no stale-value resurrection.
- [x] Backup/restore and relocation tests prove overlay checksum and effective values survive while credential data remains absent.

**Exit Criteria:**
- Existing users retain routing choices, new users have one active overlay, and all local data lifecycle operations preserve the controller contract.

### Task 3: Centralize effective controller resolution

**Purpose:**
- Make runtime routing, retry orchestration, readiness, and UI consume one effective controller configuration without policy literals.

**Files:**
- Modify: `src/fitcv/config.py`
- Modify: `src/fitcv/runtime_routing.py`
- Modify: `src/fitcv_cp/local_setup.py`
- Modify: `src/fitcv_cp/local_routes.py`
- Modify: `src/fitcv_cp/retry_settings.py`
- Verify: `tests/test_config.py`
- Verify: `tests/test_runtime_routing.py`
- Verify: `tests/test_fitcv_cp/test_local_routes.py`
- Verify: `tests/test_fitcv_cp/test_local_setup.py`
- Verify: `tests/test_fitcv_cp/test_retry_settings.py`
- Verify: `tests/test_fitcv_cp/test_queue.py`
- Verify: `tests/test_fitcv_cp/test_reconciler.py`

**Preconditions:**
- Tasks 1 and 2 complete.
- GitNexus upstream impact checks completed for config loading, routing resolution, readiness, route helpers, and retry loading before edits.

**Steps:**
- [x] Make `src/fitcv/config.py` own registries, pure validation, normalization, and deterministic merge; keep `src/fitcv_cp/local_storage.py` limited to path and file lifecycle operations.
- [x] Remove the `fitcv` to `fitcv_cp` configuration import and replace direct overlay parsing with one validated merge path: packaged defaults, local overlay, existing explicit per-run overrides.
- [x] Project provider, model routing, run retry, and prompt addenda from effective config without allowing unrelated local overrides.
- [x] Require canonical provider URL, auth mode, wire API, timeout, model routes, retry fields, and active prompt IDs; return field-specific configuration errors when missing or invalid.
- [x] Remove duplicated timeout `120`, wire API `responses`, retry-policy, prompt-ID, provider-ID, and routing-part fallback ownership from runtime and local route/setup code.
- [x] Keep safety bounds and parsing mechanics in code, but make missing canonical retry values errors instead of regenerated defaults.
- [x] Keep server/Docker behavior unchanged by applying the local overlay only when local-mode paths are explicitly active.
- [x] Return resolved values plus source indicators needed by readiness and UI without reparsing YAML in routes or templates.

**Verification:**
- [x] `./.venv/Scripts/python.exe -m pytest tests/test_config.py tests/test_runtime_routing.py tests/test_fitcv_cp/test_local_routes.py tests/test_fitcv_cp/test_local_setup.py tests/test_fitcv_cp/test_retry_settings.py tests/test_fitcv_cp/test_queue.py tests/test_fitcv_cp/test_reconciler.py -q`
- [x] Table-driven tests prove precedence and source indicators for packaged defaults, local overrides, and existing per-run overrides.
- [x] `rg -n '120|or "responses"|default=.*responses|backoff = \[1, 2, 4, 8\]|prompt_id.*v[0-9]' src/fitcv src/fitcv_cp` returns only canonical identities, validation fixtures, or documented non-owner uses reviewed in the diff.

**Exit Criteria:**
- Runtime routing, run retry, readiness, and local settings all consume one effective contract; missing defaults fail visibly instead of drifting.

### Task 4: Compose safe prompt addenda

**Purpose:**
- Add literal user guidance to supported prompts while preserving immutable response contracts and default rendering behavior.

**Files:**
- Modify: `src/fitcv/prompts/registry.py`
- Modify: `src/fitcv/prompts/renderer.py`
- Modify: `src/fitcv/prompts/templates/enrich_extraction_v1.md`
- Modify: `src/fitcv/prompts/templates/ranking_ai_score_v2.md`
- Modify: `src/fitcv/prompts/templates/cv_generation_structured_write_v1.md`
- Modify: `src/fitcv/prompts/templates/synonym_triage_recommendation_v1.md`
- Verify: `tests/test_prompts.py`
- Verify: `tests/test_config.py`

**Preconditions:**
- Task 3 effective-config shape is stable.
- Exact synonym-triage prompt asset and consumer confirmed from current source.
- GitNexus upstream impact checks completed for prompt definition lookup and rendering symbols before edits.

**Steps:**
- [x] Add one controlled addendum insertion variable to each supported prompt before its immutable output-contract section.
- [x] Apply the canonical LF/strip/4000-code-point normalization once, treat whitespace-only text as reset, and pass non-empty addenda as literal substitution values, never as templates.
- [x] Preserve byte-equivalent default prompt output when no addendum exists except for intentional whitespace normalization covered by a golden assertion.
- [x] Ensure `$`, `${...}`, conflicting instructions, Unicode, and maximum-length values render exactly once without adding template variables.
- [x] Keep active prompt IDs in `config/runtime/prompts.yaml` and validate them against the packaged prompt registry.

**Verification:**
- [x] `./.venv/Scripts/python.exe -m pytest tests/test_prompts.py tests/test_config.py -q`
- [x] Renderer tests prove addendum ordering, single insertion, fixed-contract retention, default equivalence, length bounds, and literal handling.

**Exit Criteria:**
- All supported prompts accept bounded guidance, and no user text can replace or remove packaged response-contract text.

### Task 5: Integrate prompts and hash-only provenance

**Purpose:**
- Feed effective addenda into every supported LLM stage and expose customization evidence without leaking raw text.

**Files:**
- Modify: `src/fitcv/enrich.py`
- Modify: `src/fitcv/ai_score.py`
- Modify: `src/fitcv/cv_generator.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv/pipeline_stage_artifacts.py`
- Verify: `tests/test_enrich.py`
- Verify: `tests/test_ai_score.py`
- Verify: `tests/test_cv_generator.py`
- Verify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_run_artifact_contracts.py`
- Verify: `tests/test_fitcv_cp/test_observability_contract.py`
- Verify: `tests/test_fitcv/test_telemetry.py`

**Preconditions:**
- Task 4 prompt renderer contract complete.
- GitNexus upstream impact checks completed for each stage renderer, `fitcv_cp.app._call_synonym_triage_provider`, and artifact/provenance builder before edits.

**Steps:**
- [x] Resolve each task addendum through effective config and pass it to the existing prompt renderer without adding a parallel prompt engine.
- [x] Preserve existing structured response modes, schemas, parsers, validators, grounding checks, and semantic stage rules.
- [x] Add prompt provenance fields for prompt ID/version, packaged template identity, `customized`, normalized addendum SHA-256, and character count.
- [x] Keep raw addenda out of stage artifacts, run exports, logs, diagnostics, telemetry, and HTML error content.
- [x] Add independent prompt-text and credential canaries so privacy failures identify the leaking boundary.
- [x] Verify malformed JSON/schema output remains rejected with customization enabled.

**Verification:**
- [x] `./.venv/Scripts/python.exe -m pytest tests/test_enrich.py tests/test_ai_score.py tests/test_cv_generator.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_run_artifact_contracts.py tests/test_fitcv_cp/test_observability_contract.py tests/test_fitcv/test_telemetry.py -q`
- [x] Canary scans find raw prompt text only in the overlay, explicit backup, and expected loopback settings response; credential text exists only in credential storage.
- [x] Structured-output regressions reject malformed responses for enrich, ranking, and CV generation with addenda enabled.

**Exit Criteria:**
- Every supported stage uses the same safe composition path and records useful hash-only customization evidence.

### Task 6: Add controller and prompt settings UI

**Purpose:**
- Let non-technical users inspect, edit, validate, test, save, and reset supported controller settings from the existing FitCV Local page.

**Files:**
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/local_routes.py`
- Modify: `src/fitcv_cp/local_setup.py`
- Modify: `src/fitcv_cp/templates/local_onboarding.html`
- Verify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_local_routes.py`
- Verify: `tests/test_fitcv_cp/test_local_setup.py`
- Verify: `tests/test_fitcv_cp/test_local_app.py`

**Preconditions:**
- Tasks 3 through 5 complete.
- GitNexus upstream impact checks completed for `submit_run`, onboarding routes, setup validation, readiness, and metadata helpers before edits.

**Steps:**
- [x] Render provider, wire API, auth mode, routing parts, and prompt task rows from shared registries rather than template-local lists.
- [x] Show effective provider URL, timeout, model routes, run-retry values, prompt ID/version, customization status, and source badges.
- [x] Add bounded prompt-addendum text areas and run-retry controls labeled `Run retry`; return settings responses with `Cache-Control: no-store`; do not expose per-request retry or arbitrary YAML editing.
- [x] Validate and save the full overlay atomically, preserve existing values on rejected input, and return field-specific repair messages.
- [x] Add reset actions that remove selected override/addendum keys and reveal packaged defaults without rewriting default values into the overlay.
- [x] Block new run creation on invalid effective configuration while leaving setup, recovery, existing runs, backup, diagnostics, and shutdown available.

**Verification:**
- [x] `./.venv/Scripts/python.exe -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_local_routes.py tests/test_fitcv_cp/test_local_setup.py tests/test_fitcv_cp/test_local_app.py -q`
- [x] Route/template tests prove registry-driven options, effective values, source badges, save/reset behavior, readiness blocking, and redacted errors.
- [x] Manual source-mode check confirms keyboard access, labels, error focus, and no raw prompt text in diagnostics or error pages.

**Exit Criteria:**
- Existing onboarding surface provides a repairable, accessible controller editor with no second configuration system.

### Task 7: Align managed docs and user guidance

**Purpose:**
- Update human-owned lifecycle sources and user docs without creating generated-source drift.

**Files:**
- Modify: `docs/features/admin_control_plane_core/feature.source.yaml`
- Modify: `docs/features/settings_system/feature.source.yaml`
- Modify: `docs/features/cv_system/feature.source.yaml`
- Modify: `docs/features/inspection_debugging/feature.source.yaml`
- Modify: `docs/stages/enrich.source.yaml`
- Modify: `docs/stages/ranking.source.yaml`
- Modify: `docs/stages/cv_generation.source.yaml`
- Modify: `docs/configuration.md`
- Modify: `docs/setup.md`
- Modify: `docs/usage.md`
- Generate: managed feature, stage, lineage, history, and discovery outputs through canonical sync

**Preconditions:**
- Tasks 1 through 6 define final names, paths, UI behavior, and provenance fields.

**Steps:**
- [x] Document canonical owners, effective precedence, overlay schema/path, legacy migration, reset semantics, run-retry meaning, prompt addendum bounds, privacy exclusions, and recovery behavior.
- [x] Remove `local_routing_overlay.yaml` from active-user instructions except explicit migration notes.
- [x] Update feature and stage sources with changed capabilities, invariants, tests, and prompt/controller provenance.
- [x] Run canonical architecture sync; edit human-owned sources only when generated output reveals missing semantics.
- [x] Refresh planning lineage after plan checklist/status changes during execution.

**Verification:**
- [x] `./.venv/Scripts/python.exe tools/docs/generate_architecture_metadata.py`
- [x] `./.venv/Scripts/python.exe tools/docs/generate_architecture_metadata.py --check`
- [x] `rg -n 'local_routing_overlay.yaml|120s|provider timeout.*120' docs README.md` returns only reviewed migration/history references.

**Exit Criteria:**
- Source docs, generated lifecycle outputs, and user guidance describe the implemented contract without parallel owners.

### Task 8: Prove source and packaged behavior

**Purpose:**
- Produce completion evidence across source runtime, packaging, privacy, storage, and unchanged server mode.

**Files:**
- Inspect: `packaging/windows/fitcv-local.spec`
- Modify: `scripts/smoke_fitcv_local.ps1`
- Modify: `tests/test_fitcv_local_packaging.py`
- Verify: `packaging/windows/fitcv-local.spec`
- Verify: `tests/test_deployment_config.py`
- Verify: focused and full test suites

**Preconditions:**
- Tasks 1 through 7 complete.
- Current unrelated working-tree changes remain preserved and separately identified before interpreting final diff or test failures.
- GitNexus index refreshed when possible before final `detect_changes` review.

**Steps:**
- [x] Extend packaging assertions for canonical config, immutable prompt assets, and absence of user overlay or credentials in the bundle.
- [x] Extend smoke coverage to bind runtime metadata to the started process and exercise migrated/default, customized, and reset controller scenarios.
- [x] Run one fresh packaged pipeline with a prompt addendum and one reset/default run; verify terminal/review state, structured output validity, prompt provenance, and SQLite integrity.
- [x] Scan packaged logs, diagnostics, HTML error/non-settings responses, telemetry, DB artifacts, and run exports with separate prompt and credential canaries; verify settings HTML is `no-store`.
- [x] Run focused server/developer routing, retry, queue, and deployment tests with no local overlay activation.
- [x] Run full contract, planning, architecture, packaging, and test gates; record unrelated baseline failures without fixing them.
- [x] Run GitNexus `detect_changes(scope="all")` before any commit to confirm only expected controller, prompt, local UI/storage, packaging, tests, docs, and generated outputs are affected.

**Verification:**
- [x] `./.venv/Scripts/python.exe -m pytest tests/test_config.py tests/test_runtime_routing.py tests/test_prompts.py tests/test_enrich.py tests/test_ai_score.py tests/test_cv_generator.py tests/test_fitcv_cp tests/test_fitcv_local_packaging.py tests/test_deployment_config.py -q`
- [x] `./.venv/Scripts/python.exe -m pytest -q`
- [x] `powershell -ExecutionPolicy Bypass -File scripts/build_fitcv_local.ps1`
- [x] `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke_fitcv_local.ps1 -BundlePath .\dist\fitcv-local`
- [x] Packaged customized and reset runs both reach canonical terminal/review state; `PRAGMA integrity_check` returns `ok`.

**Exit Criteria:**
- Fresh source and packaged evidence proves SSOT ownership, safe customization, privacy, migration, storage lifecycle, and server-mode compatibility.

## Execution Record

- Focused regression suite: `1448 passed, 1 skipped`.
- Full regression suite: `2221 passed, 3 skipped, 1 failed`; unrelated baseline failure remains in `tests/test_deferred_cleanup_characterization.py::test_deferred_cleanup_modules_have_no_active_src_or_test_importers` because `src/fitcv/pipeline.py` and `tests/test_pipeline_stage_resume_parity.py` still import `fitcv.pipeline_stage_runner`. Current plan did not touch those files.
- Architecture generation and `--check`: passed.
- Planning lifecycle and full repo-contract validation: passed.
- Local bundle build: passed; packaged smoke with `-BundlePath .\dist\fitcv-local`: passed.
- Packaged live evidence: customized and reset runs both `succeeded` with `checkpoint_status=awaiting_review`; customized enrich provenance is hash-only and reset provenance is default/uncustomized; SQLite integrity and foreign-key checks passed; prompt and credential canaries absent from protected surfaces; settings responses use `Cache-Control: no-store`.
- GitNexus `detect_changes(scope="all")`: aggregate worktree classified `CRITICAL` because 75 files are currently changed, including pre-existing/generated work; affected flows include expected controller, routing, retry, prompt, local UI, and packaging paths. No commit performed.
- Manual source-mode accessibility check: template inspection confirms labels, `for`/`id` pairing, `role="alert"`, `tabindex="-1"`, and `aria-live`; route/template tests cover rendered settings, errors, reset, source badges, and privacy.

## Verification

- `./.venv/Scripts/python.exe scripts/generate_planning_lineage.py`
- `./.venv/Scripts/python.exe scripts/validate_planning_lifecycle.py`
- `./.venv/Scripts/python.exe scripts/validate_template_required_sections.py`
- `./.venv/Scripts/python.exe tools/docs/generate_architecture_metadata.py --check`
- `./.venv/Scripts/python.exe scripts/validate_adoption_shape.py`
- `./.venv/Scripts/python.exe scripts/validate_repo_contracts.py --fast`
- `./.venv/Scripts/python.exe scripts/validate_repo_contracts.py`
- GitNexus `detect_changes(scope="all")` review records expected controller, prompt, local UI/storage, packaging, tests, docs, and generated-lineage effects, plus pre-existing aggregate worktree changes; no commit performed.
- `git diff --check`
- `git status --short`

Rollback policy:

- Invalid new overlay or failed migration leaves the prior valid overlay and bootstrap pointer recoverable.
- A packaged-local release may be withheld without reverting server/developer runtime.
- User reset removes override keys; it never copies packaged defaults into the overlay.
- Never roll back by restoring duplicate fallback literals, activating both overlay files, storing credentials in YAML, exporting raw prompt addenda, restoring external `fitcv-langgraph`, or deleting user data automatically.

## Completion Criteria

A plan item is considered complete when:

1. all Key Deliverables are satisfied
2. every task checklist and verification line is marked `- [x]`
3. every child item is `completed` or `dropped`
4. provider, routing, timeout, run-retry, and prompt-ID defaults have one canonical YAML owner
5. supported identities and UI labels have one shared code-registry owner
6. one validated `local_controller_overlay.yaml` is active and legacy migration is atomic and loss-safe
7. runtime, readiness, retry, routes, templates, and prompt rendering consume one effective configuration path
8. prompt addenda render once before immutable contracts and malformed structured output remains rejected
9. raw prompt text and credentials remain absent from logs, diagnostics, telemetry, HTML errors, DB artifacts, and ordinary run exports
10. backup, restore, relocation, restart, customized run, and reset/default run preserve integrity and truthful provenance
11. Docker/server mode ignores FitCV Local overlay unless local mode is explicitly active
12. source tests, packaged smoke/live proof, architecture sync, lifecycle validation, repo contracts, GitNexus scope review, and diff hygiene pass; unrelated baseline failure remains documented

Canonical source-of-truth:

<LINK>
- `docs/intent/workstreams/threads/workstream-operator-control-plane/08-fitcv-local-distribution-and-onboarding.md`
- `docs/superpowers/specs/2026-07-17-10-02-fitcv-local-controller-ssot-and-safe-prompt-customization-spec.md`
- `config/runtime/control_plane.yaml`
- `config/runtime/prompts.yaml`
- `src/fitcv/config.py`
- `src/fitcv/runtime_routing.py`
- `src/fitcv/prompts/registry.py`
- `src/fitcv/prompts/renderer.py`
- `src/fitcv_cp/local_storage.py`
- `src/fitcv_cp/local_setup.py`
- `src/fitcv_cp/local_routes.py`
- `src/fitcv_cp/retry_settings.py`
- `docs/features/admin_control_plane_core/feature.source.yaml`
- `docs/features/settings_system/feature.source.yaml`
- `docs/features/cv_system/feature.source.yaml`
- `docs/features/inspection_debugging/feature.source.yaml`
- `docs/operating_system/lifecycle/doc-system-lifecycle.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>




