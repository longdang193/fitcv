---
layer: change
artifact_type: spec
status: active
template_id: detailed-specification
name: fitcv-local-controller-ssot-and-safe-prompt-customization
parent_thread: workstream-operator-control-plane.fitcv-local-distribution-and-onboarding
targets:
  - config/runtime/control_plane.yaml
  - config/runtime/prompts.yaml
  - src/fitcv/config.py
  - src/fitcv/runtime_routing.py
  - src/fitcv/prompts
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

# FitCV Local Controller SSOT And Safe Prompt Customization Specification

## Goal

Remove remaining controller/configuration SSOT drift and add safe user-owned
prompt customization to FitCV Local without creating a second prompt engine,
an arbitrary YAML editor, or editable response contracts.

Packaged runtime defaults remain application-owned and read-only. FitCV Local
stores one narrow, versioned, non-secret controller overlay under the selected
data root. Users may change supported provider values, model routes, existing
run-retry settings, and bounded per-task prompt addenda. Fixed prompt text that
defines response format, required JSON keys, schemas, grounding constraints,
and validation rules remains packaged and non-editable.

This specification extends the existing FitCV Local distribution and onboarding
thread. Docker/server mode, pipeline semantics, and internal LLM runtime remain
unchanged except where needed to consume the same effective configuration.

## Planning Triage

- Layer: `change`
- Feature type: `MODIFY`
- Summary: centralize controller defaults and add safe prompt addenda through one user-owned local overlay
- Primary lens: `mixed`
- Affected stages: `enrich`, `ranking`, `cv_generation`
- Affected features: `admin_control_plane_core`, `settings_system`, `cv_system`, `inspection_debugging`, `run_lifecycle_controls`
- Generated refresh required: `yes`
- Capability IDs:
  - `admin_control_plane_core.jinja2-admin-pages`
  - `settings_system.settings-schema-registry`
  - `settings_system.advanced-settings-disclosure`
  - `settings_system.baseline-default-hydration`
  - `cv_system.config-owned-generation-contract`
  - `inspection_debugging.prompt-provenance-diagnostics`
- Spec needed: `yes`
- Plan needed: `yes`, after spec approval

## Key Deliverables

### Controller default ownership has one source per concern

| Concern | Canonical owner | User override | Code responsibility |
|---|---|---|---|
| Provider URL, auth mode, wire API, timeout | `config/runtime/control_plane.yaml` | local controller overlay | validate and resolve only |
| Provider IDs, provider types, auth-mode IDs, wire API IDs, routing-part IDs, prompt-addendum task IDs, and UI labels | typed registries in `src/fitcv/config.py` | none | own supported identities, labels, and validation bounds |
| Per-task provider/model selection | `config/runtime/control_plane.yaml` | local controller overlay | validate required routes |
| Run retry policy | `config/runtime/control_plane.yaml` | local controller overlay | enforce bounds and consume values |
| Active prompt IDs | `config/runtime/prompts.yaml` | none in this pass | validate against prompt registry |
| Packaged templates and fixed output contracts | prompt registry/templates and stage schemas | none | render and validate |
| User prompt customization | local controller overlay | user-owned | insert bounded addendum only |
| API credentials | OS credential store | user-owned secret store | resolve by provider ID |

Runtime defaults do not remain duplicated as fallback literals in routes,
runtime adapters, retry loaders, templates, or tests. Every configured provider
must declare `base_url`, `auth_mode`, `wire_api`, and `timeout_seconds` in
`config/runtime/control_plane.yaml`. The same file must declare every supported
routing part and all existing run-retry fields: `enabled`, `max_attempts`,
`backoff_seconds`, `lease_seconds`, `reconciler_interval_seconds`, and
`error_details_max_chars`. `config/runtime/prompts.yaml` must also declare
`synonym_triage.recommendation.prompt_id` beside the existing active prompt IDs.

### One versioned local controller overlay

Replace the routing-only local filename with:

```text
<data-root>/config/local_controller_overlay.yaml
```

The overlay is non-secret, atomically written, included in local backup, and
validated through one reader. It permits only supported controller sections:

```yaml
version: 1
providers:
  openai_compatible:
    base_url: https://example.test/v1
    auth_mode: required
    wire_api: chat_completions
    timeout_seconds: 300
model_routing:
  parts:
    enrich_extraction:
      provider: openai_compatible
      model: example-model
fitcv_cp:
  retry:
    enabled: false
    max_attempts: 1
    backoff_seconds: [1, 2, 4, 8]
    lease_seconds: 900
    reconciler_interval_seconds: 0
    error_details_max_chars: 2048
prompts:
  additional_instructions:
    enrich_extraction: |
      Prefer conservative seniority classification.
```

Unknown sections, identities, prompt keys, non-positive timeouts, invalid retry
values, and non-string prompt addenda reject before write and before new runs.

Existing `local_routing_overlay.yaml` receives one idempotent migration when the
new file does not exist and no retired legacy backup exists. Migration copies
only validated `providers` and `model_routing`, atomically writes and revalidates
the new file, then renames the exact legacy file to
`local_routing_overlay.yaml.migrated.bak`. A valid new file always wins. When both
files exist after an interrupted retirement, startup uses the new file, retries
the legacy rename, and never reimports legacy values. A failed new-file write
leaves the exact legacy file recoverable. Credentials never enter either file.
Only the new-file replacement is claimed as atomic; cross-file migration uses
this explicit recoverable sequence.

### Effective controller configuration has one merge path

Effective values resolve in this order:

1. packaged canonical defaults
2. validated FitCV Local controller overlay
3. already-supported explicit per-run overrides

`src/fitcv/config.py` owns supported registries, pure overlay validation,
normalization, and effective merge. `src/fitcv_cp/local_storage.py` owns only
local paths, atomic file I/O, migration, backup, restore, and relocation.
`src/fitcv_cp/local_setup.py`, routes, runtime routing, retry orchestration, and
prompt rendering consume those APIs. Core `fitcv` code must not import
`fitcv_cp` to resolve configuration.

Missing required fields produce actionable configuration errors. They do not
silently become `120`, `responses`, retry defaults, or hardcoded prompt IDs.
### Safe prompt customization uses addenda, not template replacement

Users can configure one optional `additional_instructions` value for each
supported LLM task:

- `enrich_extraction`
- `ranking_ai_score`
- `cv_generation_structured_write`
- `synonym_triage_recommendation`

Each packaged prompt keeps one controlled insertion point before its immutable
output-contract section. Rendering order is:

1. packaged role and task instructions
2. runtime job/candidate/evidence context
3. user additional instructions, when present
4. packaged fixed output contract and schema instructions

The user addendum is substituted as a value, not treated as a second template,
so `$` or `${...}` inside user text cannot introduce template variables. On
save, replace CRLF and CR with LF, strip surrounding whitespace, preserve
internal whitespace, and reject values above `4000` Unicode code points.
Whitespace-only values remove the overlay key. SHA-256 hashes normalized UTF-8
bytes, and character count uses the normalized string. Empty addenda render the
same effective prompt as the packaged default.

Fixed content remains non-editable:

- required JSON-only or structured-output instruction
- response schema and required keys
- grounding and non-invention constraints
- parser and validator expectations
- stage-owned semantic rules
- native structured-response mode already selected by the stage

No keyword blacklist attempts to detect instructions such as “ignore previous
instructions.” Safety comes from immutable contract placement, native structured
response enforcement where supported, and existing parser/validator rejection.

### Lightweight controller and prompt UI

Reuse the existing revisitable FitCV Local setup/onboarding page. Do not create
a desktop settings framework or arbitrary config editor.

The page contains:

- provider, API root, auth mode, wire API, and credential update controls
- default model and advanced per-task model controls
- advanced provider timeout control
- advanced existing run-retry controls
- one prompt-addendum textarea per supported task
- read-only active prompt ID/version and fixed-output-contract notice
- `Default` or `Custom` source indicator for resolved values
- save and reset-to-default actions
- warning that addenda are plaintext local configuration and are included in explicit backups

Provider choices, wire API choices, and task rows render from shared
registries/effective configuration. HTML does not repeat identity inventories.
Prompt customization stays optional and does not block onboarding when empty.
Invalid saved configuration blocks new runs with a repairable readiness message
while setup, recovery, existing runs, backup, diagnostics, and shutdown remain
available.

### Prompt customization remains private and diagnosable

Raw prompt addenda remain in the user-owned controller overlay, explicit
user-created backups, and the revisitable loopback settings form needed to edit
them. Settings responses use `Cache-Control: no-store`. Raw addenda are excluded
from normal logs, sanitized diagnostics, remote telemetry, HTML error payloads,
non-settings pages, database records, and general run/artifact exports.

Prompt provenance records only:

- prompt ID and version
- packaged template path or identifier
- `customized: true|false`
- normalized addendum SHA-256 when customized
- addendum character count
- effective model/provider routing already recorded by runtime evidence

Resetting customization removes the overlay key. Prompt history, marketplace,
sharing, and synchronization are not added.

## Task/Wave Breakdown

### Wave 1: Lock SSOT ownership and overlay schema

**Purpose:**
- convert identified drift findings into one enforceable ownership contract

**Steps:**
- [ ] define shared supported provider, wire API, auth-mode, and routing-part registries with UI labels
- [ ] declare required provider/routing/retry fields and validation bounds
- [ ] define `local_controller_overlay.yaml` schema and legacy overlay migration
- [ ] define packaged-default, local-overlay, and per-run precedence
- [ ] define prompt-addendum keys, maximum length, normalization, and reset semantics

**Verification:**
- [ ] every configurable value has one default owner and every stable identity has one registry owner
- [ ] overlay contains no secret field and no arbitrary nested configuration escape hatch

**Exit Criteria:**
- no implementation decision depends on ambiguous ownership or precedence

### Wave 2: Centralize loaders and remove duplicate defaults

**Purpose:**
- make all consumers use effective configuration instead of local literals

**Steps:**
- [ ] load and validate the controller overlay once through the config layer
- [ ] remove `120` timeout fallbacks outside canonical configuration
- [ ] remove `responses` wire-API fallbacks where canonical routing is required
- [ ] remove code-owned prompt-ID defaults duplicated from `config/runtime/prompts.yaml`
- [ ] make retry settings consume effective values while keeping only safety bounds in code
- [ ] render provider, wire API, and routing-part UI inventories from shared registries
- [ ] retain Docker/server behavior when no local overlay path is active

**Verification:**
- [ ] static scans and focused tests prove removed literals cannot regain ownership
- [ ] malformed or incomplete canonical config fails with field-specific messages
- [ ] valid existing packaged configuration resolves unchanged

**Exit Criteria:**
- routes, runtime routing, retry orchestration, and templates consume one effective contract

### Wave 3: Add bounded prompt customization

**Purpose:**
- let users guide model behavior without editing fixed response contracts

**Steps:**
- [ ] add one optional addendum insertion point to supported packaged prompts
- [ ] pass normalized addenda through effective config into `render_prompt()`
- [ ] keep fixed output contract after the addendum for every supported prompt
- [ ] keep response schema, parser, validator, and grounding ownership unchanged
- [ ] add setup UI save/reset flows with field validation and source indicators
- [ ] emit hash-only prompt customization provenance

**Verification:**
- [ ] default-empty rendering is equivalent to packaged default behavior
- [ ] custom text appears exactly once before fixed output instructions
- [ ] conflicting user text cannot remove fixed instructions or schema enforcement
- [ ] raw custom text is absent from logs, diagnostics, telemetry, and ordinary exports

**Exit Criteria:**
- users can safely customize task guidance while runtime contracts remain immutable

### Wave 4: Data lifecycle, packaged proof, and documentation

**Purpose:**
- prove user ownership, migration safety, packaging parity, and truthful docs

**Steps:**
- [ ] include controller overlay in backup/import/relocation paths
- [ ] exclude credentials and raw prompt text from sanitized diagnostics
- [ ] migrate legacy routing overlay atomically and test restart behavior
- [ ] update feature/stage sources and regenerate managed outputs
- [ ] update setup, configuration, and usage docs with ownership and reset behavior
- [ ] run source-mode and packaged-mode controller/prompt verification

**Verification:**
- [ ] backup/restore preserves controller and prompt customization
- [ ] package contains immutable default prompt assets but no user overlay
- [ ] fresh packaged run records customized prompt hash and valid structured output
- [ ] reset run records default prompt provenance and unchanged fixed contract

**Exit Criteria:**
- implementation plan can close with source, package, storage, and documentation evidence
## Design Decisions

### Decision: Separate default values from supported identities

- context: YAML values and code-supported identities have different ownership and change patterns
- choice: runtime defaults live in canonical YAML; stable supported IDs and labels live in one typed code registry
- alternatives considered:
  - derive all supported identities from user-editable YAML
  - repeat identity lists in routes, templates, and validators
- impact:
  - users can change values without redefining application capabilities
  - UI and validation stay symmetric without treating config as plugin discovery

### Decision: Use one generic local controller overlay

- context: routing, retry, and prompt addenda are non-secret user-owned controller settings
- choice: migrate the routing-only overlay to one narrow `local_controller_overlay.yaml`
- alternatives considered:
  - one file per setting family
  - extending the misleading `local_routing_overlay.yaml` name indefinitely
  - storing all values in settings SQLite
- impact:
  - one backup/migration boundary and one precedence rule
  - no database dependency for boot-time provider routing

### Decision: Missing canonical defaults are errors, not code fallbacks

- context: fallback literals caused timeout and wire-API drift while smoke still passed
- choice: validate required canonical fields and surface actionable readiness/startup errors
- alternatives considered:
  - keep matching fallback constants in code
  - warning-only behavior
- impact:
  - configuration mistakes become visible before provider calls
  - YAML remains actual runtime owner rather than documentation

### Decision: Expose existing run retry, not a new LLM-request retry engine

- context: `fitcv_cp.retry` retries run orchestration; provider HTTP retries have different duplicate-request and billing risks
- choice: centralize and expose existing run-retry settings only
- alternatives considered:
  - automatically retry every LLM timeout or transport failure
  - add provider-specific retry policy in this pass
- impact:
  - UI language must say `Run retry`
  - per-call retry remains a separate future specification if evidence requires it

### Decision: Prompt customization is addendum-only

- context: full template editing lets users delete JSON/schema and grounding requirements
- choice: users edit one bounded addendum inserted before immutable output-contract text
- alternatives considered:
  - full prompt-template editor
  - uploaded prompt files
  - arbitrary system/user message editor
- impact:
  - prompt registry, renderer, schemas, parsers, and validators stay authoritative
  - reset-to-default deletes one overlay key

### Decision: Do not filter prompt meaning heuristically

- context: phrase blacklists are brittle and cannot prove instruction safety
- choice: accept bounded text, place fixed contract after it, and enforce structured parsing/validation
- alternatives considered:
  - reject phrases such as `ignore previous instructions`
  - silently rewrite user content
- impact:
  - behavior stays predictable and explainable
  - failed structured output is a normal validation failure, never silently accepted

### Decision: Record hash-only customization provenance

- context: operators need customization visibility, but raw prompt text may contain private guidance
- choice: persist prompt metadata, customization hash, and length without raw addendum text
- alternatives considered:
  - store full effective prompt in every run artifact
  - omit customization provenance
- impact:
  - diagnostics compare runs without exporting private prompt content
  - exact historical replay after later edits is outside this pass

## Invariants

- `config/runtime/control_plane.yaml` is sole packaged owner for provider runtime values, model routing, and run-retry defaults.
- `config/runtime/prompts.yaml` is sole packaged owner for active prompt IDs.
- Code registries own allowed identities and validation bounds, not mutable runtime default values.
- No provider timeout, wire API, retry policy, or active prompt ID receives a second silent default outside its canonical owner.
- FitCV Local applies one validated non-secret controller overlay after packaged defaults.
- Application-managed credentials remain in OS credential storage and are never injected into controller YAML, prompt addenda, logs, backups, diagnostics, or telemetry.
- User customization cannot replace templates, response schemas, required keys, parser rules, validators, or grounding constraints.
- Fixed output-contract text renders after user additional instructions.
- Empty or reset customization preserves packaged default behavior.
- Raw prompt addenda remain in user-owned local configuration and explicit backups, not normal diagnostics, observability, or run artifacts.
- Invalid local controller configuration blocks new work before run creation and leaves repair/recovery routes accessible.
- Server/Docker mode ignores FitCV Local overlay unless explicitly launched with local-mode paths.
- Existing external `fitcv-langgraph` removal remains intact.

## Acceptance Criteria

- No active runtime path contains `120` as provider-timeout policy fallback.
- No active runtime path silently defaults `wire_api` when canonical provider configuration is required.
- Retry loader values match effective controller config and do not recreate YAML policy when keys are absent.
- Prompt selection fails clearly when required `config/runtime/prompts.yaml` IDs are absent or unknown.
- Provider, wire API, auth mode, and routing-part UI choices come from shared registries, not hardcoded HTML inventories.
- Existing routing overlay migrates once without losing provider or model values.
- Local controller overlay backup and restore preserve provider, model, retry, and prompt-addendum values.
- User can save and reset one addendum for every supported LLM task.
- Oversized, malformed, or unknown prompt customization fields reject with field-specific errors.
- Rendered prompts contain custom addendum exactly once and retain fixed output contract afterward.
- Existing structured-response parsers and validators reject malformed provider output after customization.
- Run/stage diagnostics expose prompt customization hash and status without raw custom text.
- Packaged smoke proves default prompt assets exist and no user overlay is bundled.
- One fresh packaged customized run and one reset/default run complete without configuration drift.
- Docker/server-focused tests retain existing behavior.

## Non-Goals

- full prompt-template editing
- custom response schemas or required JSON keys
- prompt file upload, marketplace, sharing, or version-history UI
- arbitrary YAML/config editor
- provider plugin system or SDK abstraction
- new per-LLM-request retry engine
- changing ranking thresholds, CV acceptance policy, extraction semantics, or stage response schemas
- storing credentials in controller configuration
- replacing FastAPI/Jinja UI
- restoring external `fitcv-langgraph` integration

## Risks and Mitigations

- risk: legacy routing overlay migration creates two active owners
  - mitigation: migrate atomically, activate only new path, and test old-file presence does not affect resolution
- risk: user addendum conflicts with fixed response requirements
  - mitigation: render fixed contract afterward and keep parser/schema validation authoritative
- risk: compatible provider ignores native structured-output options
  - mitigation: retain textual fixed contract plus parser/validator rejection
- risk: controller overlay grows into unrestricted config duplication
  - mitigation: exact allowlist, schema version, unknown-key rejection, and no generic recursive merge
- risk: retry controls are confused with provider request retries
  - mitigation: label controls and docs as `Run retry`; keep per-call retries out of scope
- risk: prompt addenda leak through diagnostics
  - mitigation: hash-only provenance, sensitive-log protections, and separate prompt-text and credential canary tests
- risk: strict missing-field validation blocks startup after a damaged file
  - mitigation: keep setup/recovery routes available and offer reset-to-default
- risk: dynamic UI registries expose unsupported runtime parts
  - mitigation: registry owns exact supported task set; config requires every route and rejects unknown routes
## Validation Plan

- proof target: controller defaults have one owner
  - method: static literal/owner scan plus config tests
  - evidence: no duplicate timeout, wire API, retry-policy, or active-prompt default owners

- proof target: effective precedence is deterministic
  - method: table-driven tests for packaged defaults, local overlay, and per-run overrides
  - evidence: exact resolved values and source indicators for every precedence case

- proof target: legacy overlay migration is loss-safe
  - method: temporary data-root migration tests with injected write failure
  - evidence: old file remains recoverable on failure; new file activates only after valid atomic write

- proof target: prompt addenda cannot remove fixed contracts
  - method: renderer tests with empty, normal, conflicting, dollar-containing, and maximum-length text
  - evidence: addendum appears once before immutable contract; required schema instructions remain present

- proof target: malformed structured responses remain rejected
  - method: existing enrich, ranking, and CV parser/validator tests with customization enabled
  - evidence: invalid JSON/schema output produces canonical validation failure, never accepted output

- proof target: UI mirrors canonical registries and effective values
  - method: route/template tests using changed registry/config fixtures
  - evidence: provider, wire API, task rows, timeout, retry, prompt metadata, and source badges match resolved config

- proof target: prompt privacy boundary holds
  - method: separate prompt-text and credential canary scans across overlay, backup, logs, diagnostics, telemetry, HTML error/non-settings responses, and DB artifacts; verify the settings response is `no-store`
  - evidence: prompt canary exists in overlay and explicit backup only; credential canary exists only in credential storage; both are absent from excluded surfaces

- proof target: data lifecycle preserves user configuration
  - method: backup, relocate, restore, and restart tests
  - evidence: controller overlay checksum validates and effective values survive each operation

- proof target: packaged application uses same contract as source mode
  - method: build bundle, run smoke, execute one customized and one reset/default packaged scenario
  - evidence: prompt assets exist, run reaches canonical terminal/review state, provenance is correct, SQLite integrity is `ok`

- proof target: server/developer mode remains unchanged
  - method: focused config, runtime routing, retry, queue, and deployment tests
  - evidence: no local overlay is consumed without local-mode activation and existing server tests pass

- proof target: managed documentation stays synchronized
  - method: architecture metadata sync/check, planning lifecycle validation, and repo contract validation
  - evidence: updated feature/stage sources, regenerated contracts/lineage/discovery outputs, and passing validators

## Completion Criteria

This specification is complete when:

1. ownership matrix and local controller overlay schema are approved
2. every timeout, wire API, retry, prompt-ID, provider, and routing-part SSOT finding has one explicit disposition
3. local overlay migration, validation, precedence, backup, and recovery behavior are defined
4. prompt addenda remain optional, bounded, private, and unable to replace fixed contracts
5. UI behavior, readiness failure behavior, and reset-to-default behavior are testable
6. acceptance criteria and validation evidence are implementation-plan ready
7. downstream implementation plan is completed or explicitly dropped
8. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/intent/workstreams/threads/workstream-operator-control-plane/08-fitcv-local-distribution-and-onboarding.md`
- `docs/superpowers/specs/2026-07-16-22-29-fitcv-local-distribution-and-onboarding-spec.md`
- `config/runtime/control_plane.yaml`
- `config/runtime/prompts.yaml`
- `src/fitcv/config.py`
- `src/fitcv/prompts/registry.py`
- `src/fitcv/prompts/renderer.py`
- `src/fitcv_cp/local_storage.py`
- `src/fitcv_cp/local_setup.py`
- `src/fitcv_cp/retry_settings.py`
- `docs/features/admin_control_plane_core/feature.source.yaml`
- `docs/features/settings_system/feature.source.yaml`
- `docs/features/cv_system/feature.source.yaml`
- `docs/features/inspection_debugging/feature.source.yaml`
- `docs/operating_system/lifecycle/doc-system-lifecycle.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>