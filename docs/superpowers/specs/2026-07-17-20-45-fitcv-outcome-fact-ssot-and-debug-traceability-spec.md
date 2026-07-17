---
layer: change
artifact_type: spec
status: completed
template_id: detailed-specification
name: fitcv-outcome-fact-ssot-and-debug-traceability
parent_thread: workstream-agentic-observability.agentic-observability-operator-surface
targets:
  - docs/intent/workstreams/threads/workstream-agentic-observability/02-agentic-observability-operator-surface.md
  - src/fitcv/pipeline_contracts.py
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_artifacts.py
  - src/fitcv_cp/models.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/app_run_support.py
  - src/fitcv_cp/run_artifact_mirror.py
  - src/fitcv_cp/templates/run_detail.html
  - tests/test_pipeline.py
  - tests/test_fitcv_cp
  - docs/component_boundaries.md
  - docs/observability.md
  - docs/features/inspection_debugging/feature.source.yaml
  - docs/features/trigger_run_management/feature.source.yaml
related_features:
  - inspection_debugging
  - trigger_run_management
  - cv_system
related_stages:
  - normalize
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

# FitCV Outcome Fact SSOT And Debug Traceability

## Goal

Define one compact, versioned, job-level outcome contract that explains what happened, why it happened, and where supporting evidence lives for every admissible terminal job outcome.

The upgrade must reduce capture and UI administration by reusing existing persisted events, stage artifacts, results, settings snapshots, and terminal artifact mirrors. It must not introduce another database, capture service, logging stack, or independently maintained diagnostic model.

A skipped job must be reproducible without making raw runtime internals the default user experience.

## Triage

- layer: `change`
- owning thread: `workstream-agentic-observability.agentic-observability-operator-surface`
- primary feature: `inspection_debugging`
- supporting features: `trigger_run_management`, `cv_system`
- primary lens: cross-stage outcome truth and operator projection
- plan needed after approval: yes
- roadmap or workstream reprioritization: no

## Problem Statement

FitCV already captures useful facts through several surfaces:

- `RunEvent` for chronology
- stage artifacts for stage-owned evidence and decisions
- per-job result rows and `decision_chain` for final outcomes
- settings and input snapshots for run reconstruction
- terminal artifact mirrors for local debugging
- control-plane helper dictionaries for operator presentation

The problem is repeated interpretation and presentation logic:

- equivalent outcomes can be described by different status fields and free-text messages
- skip reasons can be present in one artifact but absent or flattened in another
- UI helpers may reconstruct truth independently from persisted exports
- technical details are displayed when a user only needs a short reason
- debugging can require manually opening several files without a linking manifest
- compatibility logic for older runs can leak into multiple readers and UI paths

A job marked `skipped` must never mean "nothing happened" or "reason unavailable." It is a deterministic outcome with an owning stage, stable reason, supporting facts, and evidence reference.

## Current Source-Of-Truth Boundaries

| Concern | Existing owner | Required disposition |
| --- | --- | --- |
| Flow and lifecycle | orchestration/runtime | unchanged |
| Stage calculation and evidence | stage artifact | unchanged |
| Final cross-stage job outcome | per-job result record | normalized by this spec |
| Chronology | append-only `RunEvent` | unchanged; reference outcome facts only |
| Policy meaning | policy/stage contract | unchanged |
| Runtime settings and inputs | immutable run snapshots | unchanged |
| Operator wording | derived control-plane projection | simplified |
| Local evidence mirror | generated cache | unchanged; never authority |

No downstream surface may become a competing owner of stage meaning, reason meaning, or final job outcome.

## Key Deliverables

### Deliverable 1: Canonical `JobOutcomeFact` contract

Define one validated, versioned object for every terminal job outcome. It preserves final deterministic outcome, owning stage state, stable reason code, bounded reproducibility facts, trace identity, and evidence reference.

### Deliverable 2: Single projection path

Define one shared projector that converts canonical outcome facts into result exports, run-level counts, event references, human-readable reason text, and compact run-detail rows. No UI-specific outcome reconstruction or duplicate label taxonomy remains.

### Deliverable 3: Compatibility without historical rewrite

Define one legacy projection path for historical runs lacking a native `JobOutcomeFact`. Old rows remain readable without database rewrites or synthetic backfills. Format-specific compatibility readers may collect candidate evidence from historical result, debug, or stage-artifact shapes, but they must delegate status meaning, outcome meaning, labels, and reason taxonomy to the canonical projector.

### Deliverable 4: On-demand reproduction bundle

Extend the existing run artifact ZIP assembled from persisted artifacts and snapshots. The existing `/admin/runs/{run_id}/artifacts.zip` route remains the only run-bundle contract; its manifest becomes checksummed, redacted, disposable, and never another source of truth.

### Deliverable 5: User-first inspection surface

Define a compact UI showing outcome, stage, and reason first. Raw events, trace identifiers, fingerprints, and artifact details remain available through explicit technical drill-down or debug-bundle download.

## Task/Wave Breakdown

### Wave 1: Source-first inventory

**Purpose:**
- identify every producer and consumer of terminal job outcome meaning

**Steps:**
- [ ] inventory per-job terminal statuses, reason fields, decision chains, and free-text fallbacks across all stages
- [ ] inventory result-export, stage-artifact, event, run-detail, and debug-export consumers
- [ ] identify duplicate outcome mappings, reason-label mappings, and counters
- [ ] classify each current field as authority, projection, compatibility input, or removable duplication

**Verification:**
- [ ] every admissible outcome path has one current producer and all downstream consumers documented

**Exit Criteria:**
- no contract decision depends on an unknown status or reason path

### Wave 2: Contract and taxonomy closure

**Purpose:**
- define canonical outcome shape and one reason-code registry

**Steps:**
- [ ] define `JobOutcomeFact` fields and validation
- [ ] define canonical outcome and stage-status mapping
- [ ] consolidate reason codes under `pipeline_contracts.py`
- [ ] define bounded `reason_facts` and evidence-reference rules
- [ ] define native, legacy-projected, and incomplete compatibility states

**Verification:**
- [ ] table-driven examples cover every canonical outcome and every stage
- [ ] skipped, blocked, rejected, and held preserve distinct meanings

**Exit Criteria:**
- outcome meaning and reason ownership require no UI or storage-specific branch

### Wave 3: Projection and UI simplification design

**Purpose:**
- make every downstream surface consume the same fact

**Steps:**
- [ ] define result-export serialization
- [ ] define minimal event reference payload
- [ ] define run summary derivation
- [ ] define compact job-row and reason-drawer projection
- [ ] identify deletable UI diagnostic helpers and fields

**Verification:**
- [ ] one fact produces equivalent meaning across API, export, UI, local/server mode, retry, continue, and manual-staged execution

**Exit Criteria:**
- no user-visible outcome requires independent reconstruction

### Wave 4: Reproduction and compatibility design

**Purpose:**
- make debugging complete without another administration surface

**Steps:**
- [ ] define on-demand ZIP manifest and artifact selection
- [ ] define redaction and size boundaries
- [ ] define historical projection precedence
- [ ] define unknown future reason-code behavior
- [ ] define cleanup for generated temporary bundles

**Verification:**
- [ ] one skipped-job fixture can be explained and reproduced from persisted evidence without database mutation

**Exit Criteria:**
- compatibility and debugging are deterministic, bounded, and low-maintenance

### Wave 5: Validation and implementation readiness

**Purpose:**
- make implementation proof explicit

**Steps:**
- [ ] finalize acceptance criteria and evidence commands
- [ ] identify exact tests to extend and obsolete tests to delete
- [ ] confirm feature/doc source updates and generated refresh requirements
- [ ] confirm rollback preserves stored runs

**Verification:**
- [ ] implementation plan can be written without unresolved architecture choices

**Exit Criteria:**
- spec approved and ready for `skill-writing-plans`

## Design Decisions

### Decision: Reuse existing persistence surfaces

- context: FitCV already persists result rows, events, stage artifacts, settings, inputs, and debug payloads
- choice: add no database, table, service, queue, or external observability dependency; normalize facts through existing paths
- alternatives considered:
  - separate diagnostics database
  - full event-sourced rebuild
  - required external log aggregation
- impact:
  - administration remains limited to existing user-owned data
  - deployment and backup behavior remain unchanged

### Decision: Final job outcome has one canonical object

- context: final outcome is inferable from several fields and artifacts
- choice: `JobOutcomeFact` is the only cross-stage final job-outcome contract; stages still own local calculations and evidence
- alternatives considered:
  - reconstruct final meaning in each consumer
  - treat timeline events as final outcome authority
- impact:
  - result exports own final job outcome
  - stage artifacts remain evidence authority
  - events remain chronology authority

### Decision: Canonical contract shape

Every native outcome fact uses this shape:

```json
{
  "schema_version": "job_outcome.v1",
  "run_id": "run-123",
  "job_key": "input:42",
  "job_url": "https://example.com/job/123",
  "attempt_id": null,
  "stage": "cv_analysis",
  "stage_status": "skipped_fit_gate",
  "outcome": "skipped",
  "reason_code": "reranker_fit_below_threshold",
  "reason_facts": {
    "observed": 0.41,
    "required": 0.60
  },
  "policy_version": "cv_analysis.v3",
  "trace_id": "...",
  "evidence_ref": {
    "artifact": "cv_analysis.json",
    "fingerprint": "sha256:...",
    "record_key": "input:42"
  },
  "projection_status": "native",
  "occurred_at": "2026-07-17T18:00:00Z"
}
```

Field rules:

- `schema_version` is required and additive-only within a major version
- `run_id` and `job_key` are required identities; `job_key` is the stable run-local input occurrence key `input:<input_index>`
- `job_url` is optional display metadata, never identity authority
- `attempt_id` key is always present and may be null
- `stage` owns the terminal decision
- `stage_status` preserves native stage state
- `outcome` is `accepted`, `held`, `blocked`, `rejected`, or `skipped`
- `reason_code` is required for every outcome, including `accepted`
- `reason_facts` contains bounded JSON values required to explain or reproduce the decision
- `policy_version` is null only when policy does not participate
- `trace_id` is null only when trace context is unavailable
- `evidence_ref` points to stage evidence instead of copying it and includes `artifact`, artifact `fingerprint`, and `record_key` resolving to the same `job_key`
- `projection_status` is `native`, `legacy_projected`, or `incomplete`
- `occurred_at` is timezone-aware ISO 8601

### Decision: Fact grain and identity reuse existing run input order

- context: export rows preserve one outcome per trigger-time input occurrence, including duplicate inputs removed before enrichment
- choice: one `JobOutcomeFact` represents one exported input occurrence; `job_key` is `input:<input_index>` from the immutable run input snapshot
- supporting identities: `raw_job_fingerprint` remains content identity and normalized job URL remains lookup/display metadata; neither replaces `job_key`
- lifecycle rule: retry and continue retain the same run ID, input snapshot, input index, and job key
- impact:
  - duplicate inputs receive distinct facts without inventing another cross-run identity scheme
  - existing `raw_job_fingerprint` and normalized URL helpers remain authoritative for content and URL matching
  - cross-run comparison uses explicit content identity, not accidental reuse of run-local job keys

### Decision: Uniform semantics across all outcomes

All terminal outcomes use the same required keys. Differences are data, not schema branches.

| Outcome | Meaning | Example reason |
| --- | --- | --- |
| `accepted` | final usable result exists | `accepted` |
| `held` | bounded review or continuation required | `review_gate_manual_required` |
| `blocked` | system, upstream authority, or required evidence prevented completion | `reranker_fit_below_threshold` |
| `rejected` | attempted domain work ended negatively | `post_validation_failed` |
| `skipped` | policy intentionally omitted later work | `not_selected_by_shortlist` |

`skipped` is never a missing record, null reason, or generic log message.

Current native status mapping is exhaustive and implementation-owned by the reason registry:

| Native status or condition | Outcome | Owning stage | Canonical reason |
| --- | --- | --- | --- |
| `ranked_with_cv` or accepted CV artifact | `accepted` | `cv_generation` | `accepted` |
| `review_required` with pending resolution | `held` | `cv_generation` | normalized existing review-required reason, default `review_gate_manual_required` |
| `ranked_blocked_by_reranker_fit` / `blocked_by_reranker_fit` | `blocked` | `cv_analysis` | `reranker_fit_below_threshold` |
| `ranked_skipped_fit_gate` / `skipped_fit_gate` | `skipped` | `cv_analysis` | `cv_analysis_fit_gate_skipped` |
| `validation_failed` | `rejected` | `cv_generation` | `post_validation_failed` |
| `generation_failed` | `blocked` | `cv_generation` | `cv_generation_failed` |
| `persistence_failed` | `blocked` | `cv_generation` | `cv_persistence_failed` |
| `analysis_failed` | `blocked` | `cv_analysis` | `cv_analysis_failed` |
| `not_shortlisted` | `skipped` | `shortlist` | `not_selected_by_shortlist` |
| `shortlisted_not_scored` | `skipped` | `ranking` | `not_selected_for_scoring` |
| `scored_not_ranked` | `skipped` | `ranking` | `not_selected_in_final_ranking` |
| `rejected_after_enrichment` | `rejected` | `rule_filter` | first stable rule-filter reason, default `rule_filter_rejected` |
| `rejected_before_enrichment` | `rejected` | `normalize` | first stable pre-filter reason, default `pre_enrichment_filter_rejected` |
| `deduplicated_before_enrichment` | `skipped` | `normalize` | existing `duplicate_job_url` or `near_duplicate_job_posting` reason |
| `unknown_pipeline_state` | `blocked` | latest reached stage | `pipeline_state_unclassified` |
| legacy `ranked_no_cv` without decisive substatus | `blocked` | `cv_generation` | `legacy_ranked_no_cv_unclassified`, with `projection_status=incomplete` |

No producer or consumer may choose a different mapping locally.

### Decision: Held is a replaceable current snapshot

- context: operator review can resolve one held job to accepted or rejected
- choice: the result row stores one current `JobOutcomeFact`; resolution atomically replaces the held fact with the resolved fact
- chronology: `RunEvent` retains the held and resolved outcome fingerprints; no outcome-history list is added to the result row
- counts: only the current fact contributes to run-level counts
- impact:
  - one result row still has one authoritative fact
  - review history remains append-only without dual semantic storage

### Decision: One reason-code registry, separate human labels

- context: reason codes and display text appear in several helpers
- choice: extend `pipeline_contracts.py` as canonical reason-code registry; labels and recommended actions derive from it
- alternatives considered:
  - separate enum per UI section
  - free-text reasons from producers
- impact:
  - producers emit stable codes and facts
  - UI wording can change without changing persisted meaning
  - unknown future codes remain visible

Reason codes use stable snake_case, have one owning stage or policy family, contain no dynamic data, and are never reused with changed meaning. Measured values belong in `reason_facts`.

### Decision: One builder and validator

- context: symmetry fails when each stage hand-builds a different dict
- choice: one small builder/validator in existing pipeline contracts produces `JobOutcomeFact`; no hierarchy, plugin system, or new dependency
- alternatives considered:
  - dataclass hierarchy per stage
  - pydantic adoption for this object alone
- impact:
  - all stages share validation
  - malformed outcomes fail near producer

`reason_facts` uses fixed v1 bounds: object only, maximum 16 keys, maximum nesting depth 3, maximum 16 list items, maximum 512 characters per string, and maximum 4096 canonical UTF-8 JSON bytes. Allowed leaves are null, boolean, finite number, and string. Oversized or non-finite native facts fail producer validation rather than truncating decision evidence.

`evidence_ref` uses the exact shape `{artifact, fingerprint, record_key}`. `record_key` equals `job_key`; readers locate the corresponding stage-artifact record without scanning by mutable display text.

### Decision: Events reference outcomes; they do not duplicate them

- context: complete outcome payloads in events create another copy
- choice: outcome events store only `job_key`, `stage`, `outcome`, `reason_code`, `outcome_fingerprint`, and `evidence_ref`
- alternatives considered:
  - full fact in every event
  - chronology derived from result rows
- impact:
  - events stay small
  - final truth remains recoverable if optional event emission fails

### Decision: UI is projection, never authority

- context: technical details and duplicated mappings make UI expensive
- choice: default job inspection shows outcome, stage, one derived reason sentence, `Why?`, and `Download debug bundle`
- alternatives considered:
  - raw JSON default view
  - full runtime table on every page
- impact:
  - normal users see actionable meaning
  - developers retain explicit drill-down

`Why?` may show reason code, bounded facts, policy version, attempt ID, trace ID, evidence reference, fingerprint, and compatibility status. It must not show credentials, full prompts, private reasoning, raw provider payloads, or unrelated backend internals.

### Decision: Counts and summaries are derived

- context: persisted counters can drift from per-job truth
- choice: accepted, held, blocked, rejected, and skipped counts derive from facts; compatibility counters remain only when needed for old readers or measured query performance
- alternatives considered:
  - independently update counters at each stage
- impact:
  - UI, API, export, and tests share counting rules

### Decision: One legacy projector

- context: historical runs lack new facts and cannot be rewritten safely
- choice: one read-time projector uses this precedence:
  1. valid native `job_outcome.v1`
  2. existing `decision_chain`
  3. stage status plus current result/debug fields
  4. `legacy_unclassified` with `projection_status=incomplete`
- invalid native rule: a present malformed v1 fact or unknown major version never silently falls through to legacy evidence; it projects `invalid_native_outcome` with `projection_status=incomplete`
- forward compatibility: unknown additive fields within v1 are ignored; unknown reason codes remain visible with fallback wording
- alternatives considered:
  - mandatory migration
  - separate fallback in each reader
- impact:
  - old runs remain readable
  - uncertainty stays explicit
  - no historical mutation

### Decision: Existing run artifact bundle becomes the debug bundle

- context: reproducibility is needed and `/admin/runs/{run_id}/artifacts.zip` already provides on-demand run ZIP generation
- choice: extend the existing route, artifact selector, manifest builder, and tests; keep route and filename compatibility while changing user label to `Download debug bundle`
- alternatives considered:
  - create a second debug-bundle route or builder
  - persist one ZIP per run
  - manual file collection
- impact:
  - no dependency or long-lived copy
  - one manifest makes evidence discoverable

Bundle contains available redacted files only:

```text
fitcv-run-<run_id>-artifacts.zip
├── manifest.json
├── run.json
├── results.json
├── events.json
├── jobs-input.json
├── candidate-profile.json
├── settings-used.json
├── stage-artifacts.json
├── cv-debug.json
└── prompts-and-models.json
```

Existing manifest advances additively from `run_artifact_bundle_v6`; it records run ID, app/build version when available, filenames, schema versions, SHA-256 hashes, missing-file reasons, redaction status, and generation timestamp. `/local/system/diagnostics` remains the separate system/log bundle and is not merged with run evidence.

### Decision: No initial configuration surface

- context: capture-level and retention toggles add administration before measured need
- choice: first implementation uses fixed safe bounds and existing data-root lifecycle
- alternatives considered:
  - configurable capture levels
  - per-artifact retention settings
- impact:
  - no onboarding fields
  - configuration added only after a demonstrated divergent requirement

## Symmetry Matrix

| Dimension | Cases | Required symmetry |
| --- | --- | --- |
| Outcome | accepted, held, blocked, rejected, skipped | same keys and validation |
| Stage | normalize through CV generation | same builder and registry |
| Execution mode | run-all, manual-staged | same meaning |
| Lifecycle | initial, retry, continue | same identity and attempt rules |
| Runtime | FitCV Local, developer/server | same persisted contract |
| Data backend | SQLite | same serialization across file, DB-row JSON, mirror, and ZIP boundaries |
| Surface | export, UI, event, bundle | same outcome and reason |
| Compatibility | native, legacy-projected | same outward schema with explicit status |

Operational divergence is allowed only where required, such as null attempt ID when no attempt exists or null trace ID when tracing is disabled. Keys remain present so consumers do not branch on shape.

## Invariants

- One final job outcome has one canonical `JobOutcomeFact`.
- Stage artifacts remain authoritative for calculations and evidence.
- `RunEvent` remains authoritative for chronology, not final semantic truth.
- UI never invents or reclassifies outcome meaning.
- Every terminal job outcome has a stable non-empty `reason_code`.
- Every skipped job identifies owning stage and evidence reference.
- Equivalent outcomes use equivalent fields across stages, modes, retries, backends, and surfaces.
- Human text derives from stable codes and facts; prose is not a semantic key.
- Summaries derive from canonical facts.
- Legacy uncertainty is explicit and never presented as native truth.
- Unknown future reason codes remain inspectable.
- Present malformed native facts and unknown major versions project as `invalid_native_outcome` with `projection_status=incomplete`; they never silently fall back to legacy evidence.
- Held facts are current snapshots replaced on resolution; prior held/resolved fingerprints remain chronological event evidence.
- Debug bundles are generated views and never authority.
- Stored runs remain readable without destructive migration.
- No secrets, full hidden prompts, private reasoning, or unbounded provider payloads enter facts, normal events, HTML, or bundles.
- No new external dependency, service, or database is introduced.

## Acceptance Criteria

1. Every new terminal per-job result contains a valid `job_outcome.v1` object.
2. All canonical outcomes use the same required keys.
3. A skipped job exposes stage, stage status, reason code, bounded facts, and evidence reference.
4. Missing reason codes fail validation at producer boundary.
5. Export, UI, event reference, and debug bundle preserve same outcome and reason.
6. Run-level counts equal counts derived from facts.
7. Retry and continue preserve job identity and record attempt identity without changing semantics.
8. FitCV Local and developer/server mode emit equivalent shapes.
9. SQLite result JSON, terminal mirror, and existing artifact ZIP round-trip equivalent facts.
10. Historical runs render through one projector without database rewrite.
11. Unknown historical or future codes remain visible and do not crash readers.
12. Default UI contains no raw event dump, backend detail table, stack trace, or provider payload.
13. `Why?` exposes bounded evidence whose `{artifact, fingerprint, record_key}` resolves the exact job record.
14. Debug-bundle manifest checksums match included files.
15. Bundle excludes credential and prompt-text canaries.
16. No new runtime configuration, dependency, service, table, or durable bundle store is added.
17. Duplicate UI mappings and obsolete diagnostic builders identified by plan are deleted.
18. Retained compatibility evidence readers contain no independent outcome taxonomy and call the canonical projector for semantic defaults.

## Non-Goals

- No policy-meaning changes.
- No `RunEvent` storage redesign or full event sourcing.
- No replacement of OTel, Langfuse, or optional telemetry.
- No analytics warehouse, logging service, search index, or diagnostics DB.
- No mandatory historical backfill or schema rewrite.
- No raw provider traffic or private chain-of-thought capture.
- No attempt to place all stage evidence inside outcome fact.
- No general-purpose schema framework or plugin architecture.
- No new observability configuration in first implementation.
- No broad control-plane redesign outside outcome inspection and related technical-detail deletion.

## Risks and Mitigations

- risk: fact duplicates stage evidence
  - mitigation: store only final outcome, bounded facts, and evidence reference
- risk: reason registry becomes dumping ground
  - mitigation: codes represent stable behavior; variable details remain facts
- risk: legacy projector guesses wrong
  - mitigation: emit `incomplete` and `legacy_unclassified` instead of guessing
- risk: result facts and events drift
  - mitigation: event reference derives from same in-memory fact and fingerprint
- risk: UI becomes another technical dashboard
  - mitigation: compact default row and one bounded drawer; deeper evidence downloadable
- risk: bundles leak secrets or large payloads
  - mitigation: allowlist files/fields, redact, cap sizes, test canaries
- risk: compatibility complexity spreads
  - mitigation: one projector with explicit precedence
- risk: derived counts cost too much
  - mitigation: derive first; materialize only after measured need with reconciliation tests

## Validation Plan

- proof target: outcome contract is structurally symmetric
  - method: table-driven tests for every canonical outcome and stage
  - evidence: identical required-key set and valid semantics for all fixtures

- proof target: skipped jobs remain explainable and reproducible
  - method: pipeline fixture reaching `skipped_fit_gate` with known observed and required values
  - evidence: fact, event reference, UI, and stage artifact share stage/reason; facts reproduce decision

- proof target: producer validation prevents missing reasons
  - method: unit tests with empty or invalid required fields
  - evidence: deterministic errors at shared builder

- proof target: reason taxonomy has one owner
  - method: source scan and registry/label tests
  - evidence: no stage or template maintains competing reason mapping

- proof target: summaries derive from facts
  - method: mixed-outcome fixture
  - evidence: API/export/UI counts equal direct fact counts

- proof target: lifecycle modes are symmetric
  - method: equivalent initial, retry, continue, run-all, and manual-staged tests
  - evidence: same identity and shape; attempt differs only where required

- proof target: storage representation is symmetric
  - method: round-trip the same fact through SQLite result JSON, terminal mirror payload, and existing artifact ZIP
  - evidence: equivalent decoded facts without a speculative remote-backend adapter

- proof target: historical compatibility is truthful
  - method: native, decision-chain-only, status-only, and ambiguous fixtures
  - evidence: one projector emits `native`, `legacy_projected`, or `incomplete` without writes

- proof target: UI is user-first
  - method: route/template tests
  - evidence: compact outcome, stage, reason, `Why?`, and bundle action present; raw technical detail absent by default

- proof target: bundle is deterministic and non-authoritative
  - method: build twice from same fixtures and inspect manifest
  - evidence: included-file SHA-256 values match bytes; generation metadata may differ; no DB write or durable ZIP required

- proof target: privacy boundary holds
  - method: credential, prompt-text, and oversized-provider-payload canary tests
  - evidence: canaries absent from facts, events, HTML, and bundle

- proof target: live behavior remains truthful
  - method: one admissible live run with skipped or blocked job
  - evidence: artifacts, UI, and downloaded bundle reconcile to same outcome/reason

- proof target: managed docs remain synchronized
  - method: architecture sync/check, planning lifecycle validation, and repo validation
  - evidence: updated feature sources and generated contracts/lineage pass validators

## Implementation Constraints

- Extend existing helpers before creating modules.
- Use standard-library JSON, hashing, and ZIP support.
- Keep one small builder/validator and one compatibility projector.
- Delete obsolete mappings before adding wrappers.
- Add no configuration key without demonstrated divergent requirement.
- Persist no derived human labels.
- Change no policy semantics while normalizing representation.
- Preserve current run and artifact APIs, especially `/admin/runs/{run_id}/artifacts.zip`; no second run-bundle route is allowed.

## Rollout And Rollback

### Rollout

1. add contract, builder, validator, and compatibility projector
2. emit native facts for one bounded late-stage path while readers accept native and legacy shapes
3. extend producer coverage stage by stage using same builder
4. move export, summaries, events, and UI to shared projector
5. extend existing `/admin/runs/{run_id}/artifacts.zip` manifest, redaction, and user label
6. delete duplicated mappings and obsolete technical UI

No dual-write of independently constructed semantic objects is allowed. Legacy fields may remain during migration, but new fields derive from canonical fact.

### Rollback

- readers continue accepting existing legacy fields
- disabling native emission does not make existing runs unreadable
- rollback never deletes or rewrites historical artifacts
- bundle generation can be removed independently because it is derived
- UI falls back to shared compatibility projector, not old duplicated mappings

## Completion Criteria

This specification is complete when:

1. ownership matrix is approved
2. `JobOutcomeFact` shape, validation, and reason taxonomy are approved
3. symmetry covers every outcome, stage, mode, lifecycle path, backend, and surface
4. legacy projection precedence and uncertainty behavior are approved
5. compact UI and on-demand bundle boundaries are approved
6. acceptance criteria and validation evidence are implementation-plan ready
7. affected feature and cross-cutting doc source updates are identified
8. downstream implementation plan is completed or explicitly dropped
9. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/intent/workstreams/threads/workstream-agentic-observability/02-agentic-observability-operator-surface.md`
- `docs/superpowers/specs/2026-04-28-deterministic-truth-outcome-contract-spec.md`
- `docs/superpowers/specs/2026-05-24-15-32-fitcv-cp-run-artifact-ssot-spec.md`
- `docs/component_boundaries.md`
- `docs/observability.md`
- `src/fitcv/pipeline_contracts.py`
- `src/fitcv/pipeline.py`
- `src/fitcv_cp/models.py`
- `src/fitcv_cp/run_artifact_mirror.py`
- `docs/features/inspection_debugging/feature.source.yaml`
- `docs/features/trigger_run_management/feature.source.yaml`
- `docs/operating_system/lifecycle/doc-system-lifecycle.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>