---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: cv-review-markdown-integrity-spec
parent_thread: workstream-bounded-agentic-cv-quality.agentic-cv-quality-generation-repair
targets:
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/bq_store.py
  - src/fitcv/pipeline_stage_artifacts.py
  - tests/test_fitcv_cp/
related_features: []
related_stages:
  - cv_generation
---

## Goal

Define durable design that guarantees approved CV artifacts persist full draft markdown, while keeping debug/review payload size bounded and preserving existing HITL review workflows.

## Key Deliverables

### Deliverable 1: Dual-field markdown contract for review-required debug records

Specify canonical field split between persistence-grade markdown and preview-grade markdown, with explicit ownership and compatibility behavior.

### Deliverable 2: Safe finalize contract for HITL approve path

Specify finalize-time source selection and hard rejection rules so truncated payloads cannot be written to `cv_versions`.

### Deliverable 3: Backfill and verification design

Specify repair workflow for already-truncated rows and full validation evidence required before implementation handoff.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- pin exact truncation-to-persistence leak path
- define affected interfaces and persistence boundaries

**Steps:**
- [ ] map `cv_generation_debug_json` producer and consumers
- [ ] map HITL queue preview derivation and approve-finalize write path
- [ ] map sentinel/truncation markers and where they are introduced
- [ ] map run-level artifacts available for legacy fallback/recovery

**Verification:**
- [ ] source trace shows single causal chain from debug truncation to `cv_versions.cv_markdown`

**Exit Criteria:**
- no contract decision depends on implicit behavior

### Wave 2: Decision closure

**Purpose:**
- close contract design across payload schema, UI preview, and persistence path

**Steps:**
- [ ] define new debug record markdown fields and allowed transformations
- [ ] define finalize source precedence and failure behavior
- [ ] define backward-compatible read behavior for pre-change runs
- [ ] define recovery rules for already persisted truncated artifacts

**Verification:**
- [ ] each affected interface (`worker_job`, `app`, persistence boundary) has deterministic contract

**Exit Criteria:**
- design blocks truncation leakage without increasing review UX risk

### Wave 3: Validation and approval readiness

**Purpose:**
- convert design into testable acceptance criteria and evidence gates

**Steps:**
- [ ] define unit/integration test matrix
- [ ] define data-repair verification method
- [ ] define rollout guardrails and observability checks

**Verification:**
- [ ] proof plan can detect regressions in both new and legacy run payloads

**Exit Criteria:**
- spec ready for implementation-plan handoff

## Design Decisions

### Decision: Split markdown into persistence-grade vs preview-grade fields

- context: `markdown_final` currently serves both debug/preview and persistence; debug truncation modifies same field.
- choice:
  - introduce `markdown_full` as authoritative persistence field for review-required records.
  - introduce `markdown_preview` as bounded field for UI/debug display.
  - keep legacy `markdown_final` read compatibility during migration window only.
- alternatives considered:
  - remove all truncation: rejected due payload growth and telemetry/UI overhead.
  - keep single field + ad-hoc fallback: rejected due latent contract ambiguity.
- impact:
  - `worker_job` owns bounded preview generation.
  - `app` review queue consumes preview field only.
  - finalize path consumes full field only.

### Decision: Enforce finalize-time truncation guard

- context: legacy data and mixed payloads may still contain sentinel-clipped markdown.
- choice:
  - finalize must reject markdown ending with known truncation sentinels (`...[truncated]`, `...[truncated in review queue]`).
  - rejection classified as deterministic persist block reason (`truncated_draft_blocked`).
- alternatives considered:
  - silently persist legacy value: rejected; preserves corruption path.
  - auto-regenerate inline without operator signal: rejected; hides state transition.
- impact:
  - no new truncated rows can enter `cv_versions` after rollout.
  - operator receives explicit failure reason; can regenerate or recover.

### Decision: Compatibility-first read precedence

- context: pre-change runs already stored only `markdown_final`.
- choice:
  - precedence in finalize path:
    1. `markdown_full`
    2. legacy `markdown_final` if present and not sentinel-truncated
    3. fail `missing_draft_for_approve`
  - queue preview precedence:
    1. `markdown_preview`
    2. bounded view derived from `markdown_full`
    3. bounded view from legacy `markdown_final`
- alternatives considered:
  - strict new-schema-only: rejected due immediate breakage on existing review queues.
- impact:
  - rolling deployment safe across old/new run payloads.

### Decision: Add explicit recovery workflow for already-truncated artifacts

- context: run `f6faa587-faa8-43a7-aa80-ed706a54a121` already contains truncated persisted artifacts.
- choice:
  - define scriptable recovery pass:
    - detect `cv_versions.cv_markdown` with truncation sentinel
    - rerun generation/finalize for affected job URLs using run context
    - persist corrected version rows and attach audit event
- alternatives considered:
  - manual ad-hoc patching in DB: rejected due low reproducibility and weak audit trail.
- impact:
  - deterministic remediation path for historical data quality.

## Invariants

- Approved CV artifact markdown must equal full generated draft content for that review decision.
- Preview truncation is display-only and must never mutate persistence-grade source markdown.
- `cv_versions.cv_markdown` must never end with known truncation sentinel markers.
- Backward compatibility must not permit silent corruption.
- HITL lifecycle state transitions remain unchanged (`approve_as_is`, `regenerate_once`, `reject`).

## Acceptance Criteria

1. For review-required records with markdown length > 4000 chars, approval persists full markdown without sentinel suffix.
2. Queue UI still renders bounded preview safely without reading persistence-grade field directly for clipping.
3. Legacy payloads (only `markdown_final`) remain actionable when value is intact.
4. Legacy payloads containing sentinel-truncated value are blocked from persistence with explicit terminal reason.
5. Recovery workflow can repair previously truncated artifacts and emits verifiable audit evidence.

## Non-Goals

- Redesign of CV writing prompt quality or markdown style.
- Changes to ranking, analysis, or shortlist logic.
- Migration of all historical run payload schemas beyond fields needed for markdown integrity.
- Public-repo publication workflow changes.

## Risks and Mitigations

- Risk: mixed schema reads break review queue rendering.
  - Mitigation: explicit read precedence and integration test coverage for old/new payload shapes.
- Risk: false-positive truncation detection blocks valid markdown.
  - Mitigation: sentinel checks restricted to exact known suffix markers and normalized whitespace handling.
- Risk: recovery workflow regenerates non-deterministic content.
  - Mitigation: bind recovery to same run settings/model context and capture version/audit linkage.
- Risk: payload growth from adding `markdown_full`.
  - Mitigation: keep preview bounded; avoid duplicate large field writes where status not `review_required`.

## Validation Plan

- proof target: truncation sentinel can no longer persist through approve flow
  - method: integration test (`review_required -> approve_as_is`) with >4000-char draft
  - evidence: test asserts persisted `cv_versions.cv_markdown` does not end with truncation sentinel and equals full fixture

- proof target: queue rendering remains bounded and stable
  - method: unit tests for queue item assembly using old and new payload shapes
  - evidence: snapshot/explicit assertions for `cv_markdown_preview` length and suffix behavior

- proof target: backward compatibility path remains deterministic
  - method: unit tests for finalize precedence (`markdown_full`, legacy `markdown_final`, missing case)
  - evidence: branch-specific assertions on returned `(ok, reason, version_id)`

- proof target: blocked truncated legacy drafts return explicit reason
  - method: unit test with legacy sentinel payload
  - evidence: `truncated_draft_blocked` surfaced and no insert into `cv_versions`

- proof target: historical data repair workflow is repeatable
  - method: dry-run + apply-run tests over seeded sqlite fixture containing truncated rows
  - evidence: before/after row diff and emitted run event/audit payload

## Completion Criteria

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`
4. implementation plan is drafted from this spec with explicit test matrix and rollback notes
