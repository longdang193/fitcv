---
layer: change
artifact_type: spec
status: completed
template_id: detailed-specification
name: fitcv-llm-runtime-spine-phase-1-cv-analysis-single-owner
parent_thread: workstream-operator-control-plane.fitcv-cp-app-ssot-symmetry-refactor
parent_spec: docs/superpowers/specs/2026-07-14-12-13-fitcv-llm-runtime-spine-master-spec.md
targets:
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/contracts.py
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_runner.py
  - src/fitcv/late_stage_contract.py
  - src/fitcv/evidence.py
  - src/fitcv/gap_analysis.py
  - src/fitcv/reuse.py
  - src/fitcv/pipeline_observability.py
  - src/fitcv/pipeline_stage_artifacts.py
  - src/fitcv/pipeline_stages/common.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/worker_job.py
  - docs/stages/cv_analysis.source.yaml
  - docs/stages/cv_analysis.yaml
  - docs/pipeline.md
  - docs/architecture.md
  - tests/test_agentic_cv_analysis.py
  - tests/test_pipeline.py
  - tests/test_pipeline_agentic_late_stage.py
  - tests/test_pipeline_stage_resume_parity.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_worker_job.py
related_features:
  - cv_system
  - inspection_debugging
  - settings_system
  - trigger_run_management
related_stages:
  - ranking
  - cv_analysis
  - cv_generation
---

# Detailed Spec: FitCV LLM runtime spine Phase 1 CV-analysis single owner

## Goal

Collapse current CV-analysis semantic duplication into one repo-native business
entrypoint:

`fitcv.agentic_cv_analysis.analyze_ranked_job(...) -> CvAnalysisRecord`

`pipeline.py` and `pipeline_stage_runner.py` may batch, schedule, retrieve reuse
candidates, persist records, derive downstream debug projections, and emit
observations. They must not independently decide reranker blocking, evidence
selection, fallback selection, gap meaning, fit-gate outcome, record shape,
error classification, or generation readiness.

Phase 1 is an owner-collapse change, not shared LLM-runtime extraction. CV
analysis is not currently a fully routed LLM surface, so this phase introduces
no new adapter interface and no LangGraph dependency. If current built-in and
"agentic" branches have no remaining semantic difference, the duplicate branch
is deleted rather than preserved behind an abstraction.

## Key Deliverables

### Deliverable 1: one canonical CV-analysis entrypoint

`analyze_ranked_job` owns the complete per-job semantic flow for fresh,
reranker-blocked, fit-gate-skipped, failed, and exact-reuse cases.

Canonical call shape:

```python
analyze_ranked_job(
    job,
    profile,
    config,
    *,
    top_k=None,
    reusable_record=None,
) -> CvAnalysisRecord
```

`reusable_record` is optional. Pipeline may locate a candidate record from
persisted state, but analyzer verifies fingerprint compatibility and decides
whether reuse is valid. Only successful semantic outcomes
(`ready_for_generation` and `skipped_fit_gate`) are reusable. Failed records are
recomputed; reranker blocks are reevaluated from current ranking input.
Incomplete records or records built under a different CV-analysis contract are
not upgraded in place; they are recomputed through the canonical flow.

### Deliverable 2: one canonical `CvAnalysisRecord`

`CvAnalysisRecord` and `build_cv_analysis_record` in
`agentic_cv_analysis.py` become sole owners of analysis output shape and status
semantics.

Canonical field groups:

- identity:
  - `raw_job_fingerprint`
  - `job_url`
  - `job_title`
  - `job_snapshot`
  - `analysis_input_fingerprint`
  - `analysis_input_components`
- reuse:
  - `analysis_reuse_status`
  - `reuse_decision`
- decision:
  - `status`
  - `ranking_fit_label`
  - `fit_classification`
  - `decision_chain`
- grounded analysis:
  - `evidence_payload`
  - `evidence_used`
  - `evidence_selection_summary`
  - `gap_summary`
  - `requirement_coverage`
  - `section_confidence_hints`
  - `do_not_claim`
- diagnostics:
  - `outcome_reason`
  - `error`
  - `cv_analysis_trace`

`raw_job_fingerprint` is primary per-job identity. `job_url` is descriptive and
serves only as the existing normalized compatibility fallback when the minimal
admissible input has no raw fingerprint. Analyzer, pipeline reuse lookup, trace
`record_id`, and trace `scope_key` reuse `job_identity_keys`; no second identity
resolver is added. Mutable URL is excluded from semantic input fingerprinting.
Changing fingerprint payload shape requires incrementing
`CV_ANALYSIS_REUSE_SCHEMA_VERSION`. Reranker-blocked records may omit
`analysis_input_fingerprint`, but they still retain canonical job identity.

`pre_writing_decision`, `readiness_diagnostics`, structured CV content,
validation, repair, render, and persistence fields are not CV-analysis-owned.
They remain `cv_generation` concerns.

### Deliverable 3: one status and error contract

Canonical status vocabulary remains defined by `late_stage_contract.py`:

- `blocked_by_reranker_fit`
- `skipped_fit_gate`
- `analysis_failed`
- `ready_for_generation`

Expected decision outcomes use `outcome_reason` and leave `error` empty:

- `blocked_by_reranker_fit`
- `skipped_fit_gate`

Unexpected runtime failures use `error` and leave `outcome_reason` empty:

- `analysis_failed`

`ready_for_generation` leaves both empty.

Trust-boundary violations may raise before analysis starts: `job`, `profile`,
and `config` must be mappings, and explicit `top_k` must be an integer when
present. After those inputs are accepted, reranker resolution, fingerprint
construction, reuse validation, evidence selection, gap computation, fit
decision, record construction, and trace construction are one per-job failure
envelope. Any unexpected exception in that envelope returns `analysis_failed`.

### Deliverable 4: pipeline and stage runner become thin callers

Pipeline-owned and stage-runner-owned copies of these semantics are deleted:

- reranker skip record construction
- fresh-versus-reuse semantic decision
- evidence bundle selection and fallback
- evidence-selection summary construction
- gap computation
- fit-gate classification
- analysis error classification
- CV-analysis record construction
- readiness filtering based on local string literals

Remaining orchestration consumes canonical records and status constants.
Observability and artifact builders derive projections from a complete
`CvAnalysisRecord`; they do not reconstruct business decisions.

## Task/Wave Breakdown

### Wave 1: Freeze current contract and parity fixtures

**Purpose:**
- preserve required behavior before deleting duplicate owners

**Steps:**
- [x] inventory every `CvAnalysisRecord` field consumed by CV generation,
      observability, stage artifacts, worker summaries, and control-plane views
- [x] inventory current fresh, blocked, reused, skipped, ready, and failed paths
      in analyzer, pipeline, and stage runner
- [x] define deterministic parity fixtures for each admissible outcome
- [x] add identity fixtures for URL drift, duplicate URLs with distinct raw
      fingerprints, and minimal inputs without raw fingerprints
- [x] add reuse fixtures for incomplete records and contract-version mismatch
- [x] identify fields that belong to CV generation and must leave analysis output

**Verification:**
- [x] field inventory distinguishes required contract fields from branch-local
      debug baggage
- [x] parity fixture set covers every canonical status and reuse path

**Exit Criteria:**
- no output field or status behavior is preserved only because one duplicate
  branch happens to emit it

### Wave 2: Complete canonical analyzer contract

**Purpose:**
- make `analyze_ranked_job` sufficient for all per-job analysis cases

**Steps:**
- [x] extend canonical record type and builder with required identity and reuse
      fields currently hydrated in pipeline
- [x] reuse `job_identity_keys` for canonical record, trace, and reuse identity;
      keep normalized URL only as compatibility fallback
- [x] remove mutable URL from CV-analysis semantic fingerprint payload and bump
      `CV_ANALYSIS_REUSE_SCHEMA_VERSION`
- [x] move exact-match reuse validation, reusable-status eligibility, and
      canonical record rebinding into analyzer boundary
- [x] require current contract fingerprint and complete canonical field set
      before reuse; recompute incompatible or incomplete candidates
- [x] keep reranker gate, evidence selection, fallback, gap computation, fit
      decision, record build, and trace build in one semantic flow
- [x] place all accepted per-job runtime work inside one failure envelope
- [x] use status constants from `late_stage_contract.py`; remove local status
      spelling where canonical constants exist
- [x] keep `top_k` override optional and otherwise use configured
      `pipeline.evidence_top_k`

**Verification:**
- [x] one analyzer call returns complete canonical record for every fixture
- [x] reuse candidate with mismatched fingerprint cannot be reused
- [x] canonical builder alone controls `outcome_reason` versus `error`

**Exit Criteria:**
- analyzer output needs no semantic hydration by pipeline before downstream use

### Wave 3: Delete pipeline and stage-runner semantic branches

**Purpose:**
- remove second and third meaning owners

**Steps:**
- [x] replace pipeline built-in versus agentic CV-analysis selection with one
      analyzer call
- [x] remove `agentic_late_stage_enabled` as CV-analysis semantic selector
- [x] delete pipeline-local CV-analysis record builder and hydration helpers that
      duplicate canonical builder behavior
- [x] delete stage-runner reranker-skip, reuse, and compute helpers that rebuild
      analysis semantics
- [x] keep batch scheduling, persistence, observation emission, and downstream
      debug projection outside analyzer
- [x] keep Phase 1 CV-analysis scheduling serial; retain configured concurrency
      only as observational input and report effective concurrency as `1`
- [x] use `is_generation_ready` or canonical status constant for readiness
      filtering

**Verification:**
- [x] residue search finds no pipeline or stage-runner evidence-selection, gap,
      fit-gate, or record-building branch
- [x] retained compatibility labels do not change analysis output

**Exit Criteria:**
- every ranked job reaches one analyzer entrypoint regardless of launch path or
  compatibility mode

### Wave 4: Contract and stage-doc closeout

**Purpose:**
- lock owner boundary and prevent semantic duplication from returning

**Steps:**
- [x] move analyzer-focused tests to `tests/test_agentic_cv_analysis.py`
- [x] keep pipeline tests focused on scheduling, persistence, observation, and
      artifact projection
- [x] update `cv_analysis.source.yaml`, pipeline docs, and architecture docs only
      where owner wording changes
- [x] add residue checks for deleted helpers and mode-based semantic branches

**Verification:**
- [x] repo validators and focused tests pass
- [x] generated architecture docs are synchronized if stage source changes

**Exit Criteria:**
- Phase 1 owner collapse is executable, documented, and ready for implementation
  planning

## Design Decisions

### Decision: `analyze_ranked_job` is sole business entrypoint

- context: `agentic_cv_analysis.py`, `pipeline.py`, and
  `pipeline_stage_runner.py` currently contain equivalent analysis flow.
- choice: keep existing analyzer entrypoint and move missing reuse/identity
  behavior into it rather than creating a new service or class.
- alternatives considered:
  - create `CvAnalysisService` around one function
  - keep separate built-in and agentic business methods with parity tests
- impact:
  - smallest owner collapse
  - existing direct analyzer tests remain useful
  - pipeline loses business-policy dependencies

### Decision: no CV-analysis adapter abstraction in Phase 1

- context: current alternate branch duplicates deterministic repository logic;
  no independent provider transport requires an adapter contract.
- choice: delete duplicate method. Add a private adapter seam later only when a
  real alternate evidence provider changes mechanics without changing semantics.
- alternatives considered:
  - retain `builtin` and `agentic` adapters preemptively
  - route CV analysis through LangGraph now
- impact:
  - no one-implementation interface
  - Phase 1 stays independent from Phase 2 shared runtime design

### Decision: pipeline may locate reuse candidates but analyzer owns reuse validity

- context: persistence/index lookup is orchestration, while fingerprint matching,
  rebinding, and reuse status are stage semantics.
- choice: pipeline supplies at most one candidate record. Analyzer computes the
  current fingerprint, verifies exact identity, contract, status, and field-set
  compatibility, and either reuses or performs fresh analysis.
- alternatives considered:
  - keep full reuse decision and record mutation in pipeline
  - move persistence/index lookup into analyzer
- impact:
  - storage remains outside stage logic
  - reuse behavior is identical for fresh run, replay, and resume

### Decision: Phase 1 keeps CV-analysis scheduling serial

- context: owner collapse does not require changing execution concurrency, and
  ordering-only tests do not prove provider or side-effect safety.
- choice: delete mode-specific executors and run the canonical analyzer serially
  in Phase 1. Preserve configured concurrency for diagnostics, with effective
  concurrency reported as `1`.
- alternatives considered:
  - enable concurrency for all compatibility modes during owner collapse
  - retain a mode-specific scheduling branch
- impact:
  - Phase 1 changes semantic ownership only
  - shared concurrency can be enabled later with dedicated parity proof

### Decision: one record builder owns all status shapes

- context: pipeline-local and analyzer-local builders currently emit different
  fields and diagnostic richness.
- choice: merge required fields into canonical `CvAnalysisRecord`; every newly
  returned status shape, including eligible reuse, is emitted through
  `build_cv_analysis_record`. Candidate dictionaries are never returned directly,
  and downstream code consumes records without semantic hydration.
- alternatives considered:
  - keep pipeline enrichment wrapper
  - maintain separate minimal and full record types
- impact:
  - one schema for direct, pipeline, worker, replay, and test paths
  - missing fields fail at owner boundary instead of being guessed downstream

### Decision: observations and artifacts are projections, not owners

- context: pipeline and control-plane need run IDs, counts, debug payloads, and
  persistence references that do not belong in pure per-job analysis inputs.
- choice: analyzer returns complete semantic record and stage trace. Existing
  observation/artifact helpers consume that record plus run context.
- alternatives considered:
  - pass reporter and run ID into analyzer
  - let each projection infer status and evidence independently
- impact:
  - analyzer remains deterministic and directly testable
  - one semantic record feeds every presentation surface

## Invariants

- `agentic_cv_analysis.analyze_ranked_job` is sole per-job CV-analysis business
  entrypoint.
- `CvAnalysisRecord` and `build_cv_analysis_record` have one owner in
  `agentic_cv_analysis.py`.
- `late_stage_contract.py` remains sole status-vocabulary owner.
- Reranker `skip` always produces `blocked_by_reranker_fit` before evidence or
  gap work.
- Exact reuse requires matching `analysis_input_fingerprint` and an eligible
  status (`ready_for_generation` or `skipped_fit_gate`), current contract
  fingerprint, and complete canonical fields; mismatch, failure, block,
  incomplete shape, or absent fingerprint triggers fresh evaluation.
- `raw_job_fingerprint` is primary identity across analyzer, trace, reuse,
  replay, and resume. Normalized URL is fallback only.
- `analysis_input_fingerprint` is present for fresh and reused analysis records;
  it may be empty only when reranker blocks before analysis begins.
- Mutable URL is not part of semantic input fingerprinting.
- Accepted per-job runtime failures return `analysis_failed`; they do not escape
  through one launch path while becoming records in another.
- Evidence bundle selection runs before fallback selection. Fallback runs only
  when bounded selected evidence is empty.
- `evidence_selection_summary.fallback_used` reflects actual fallback use.
- Gap computation uses one canonical candidate-skill normalization path.
- Fit-gate `skip` after analysis produces `skipped_fit_gate`, not reranker block.
- `ready_for_generation` is the only generation-ready analysis status.
- Expected blocks/skips use `outcome_reason`; unexpected failures use `error`.
- `do_not_claim` is derived from unsupported/missing requirements, never invented
  downstream.
- Pipeline and stage runner do not call `retrieve_evidence_bundle`,
  `retrieve_evidence`, `compute_gap`, or record builders for CV-analysis meaning.
- `agentic_late_stage_enabled` and similar compatibility labels cannot change
  CV-analysis semantics.
- Phase 1 CV-analysis scheduling is serial for empty, single-item, and mixed
  status batches.
- CV generation does not recompute evidence, gap, or fit decisions from job and
  profile when canonical analysis record exists.

## Acceptance Criteria

- Same ranked job, profile, config, and reuse candidate produce same canonical
  record regardless of direct, pipeline, stage-runner, worker, replay, or resume
  path.
- Canonical analyzer handles:
  - reranker block
  - fresh bundle-selected evidence
  - fallback evidence
  - empty evidence
  - fit-gate skip
  - ready for generation
  - analysis exception
  - exact reusable ready/skipped record
  - failed or blocked reusable candidate
  - mismatched reusable record
  - incomplete reusable record
  - reusable record from a different contract version
  - same raw job with changed URL
  - duplicate URL with distinct raw job fingerprints
  - explicit `top_k` override
  - minimal admissible job/profile payload
- Pipeline fixtures cover empty, single-item, and mixed-status batches.
- Pipeline and stage runner contain no branch that chooses separate CV-analysis
  semantics from compatibility mode.
- Pipeline and stage runner contain no local CV-analysis record builder.
- Canonical output preserves status, evidence summary, gap, requirement coverage,
  section confidence, `do_not_claim`, decision chain, reuse decision, and trace.
- CV-generation and control-plane tests consume canonical records without field
  synthesis or status guessing.
- Residue checks find no copied CV-analysis evidence/fallback/gap/fit flow outside
  canonical analyzer.

## Non-Goals

- extracting shared LLM runtime contract
- migrating enrichment or ranking
- changing ranking thresholds or fit-label meaning
- redesigning evidence retrieval or semantic-alignment algorithms
- changing gap-analysis math
- moving persistence, batch scheduling, or reporter lifecycle into analyzer
- enabling shared CV-analysis concurrency
- renaming `agentic_cv_analysis.py` or `analyze_ranked_job` solely for aesthetics
- redesigning CV-generation validation, repair, rendering, or persistence
- adding a CV-analysis adapter interface without a real second mechanics provider

## Risks and Mitigations

- Risk: canonical analyzer loses pipeline-only reuse metadata.
  - mitigation: inventory downstream fields first and add only required identity
    and reuse fields to canonical record.
- Risk: moving reuse validity changes resume behavior.
  - mitigation: fixtures cover exact ready/skipped reuse plus mismatch, missing
    fingerprint, incomplete shape, contract mismatch, blocked candidate, and
    failed candidate recomputation.
- Risk: URL drift splits identity or invalidates semantic reuse.
  - mitigation: use existing `job_identity_keys`, keep URL as fallback only, and
    test URL drift plus duplicate-URL cases.
- Risk: failures before evidence retrieval escape the canonical record contract.
  - mitigation: define trust-boundary validation separately and wrap all accepted
    per-job runtime work in one failure envelope.
- Risk: deleting mode branch removes hidden behavior.
  - mitigation: compare deterministic outputs before deletion; preserve only
    documented semantic differences, not branch labels.
- Risk: pipeline still reconstructs decisions for debug artifacts.
  - mitigation: debug builders accept canonical record and project fields without
    invoking analysis helpers.
- Risk: analyzer becomes coupled to run/reporting infrastructure.
  - mitigation: keep run ID, reporter, persistence, and aggregate counts outside
    analyzer.

## Validation Plan

- proof target: canonical analyzer owns every status outcome
  - method: focused unit tests in `tests/test_agentic_cv_analysis.py`
  - evidence: deterministic fixtures cover all four statuses plus fresh/reused
    subcases and assert `outcome_reason` versus `error`

- proof target: reuse semantics have one owner
  - method: exact-match, status-eligibility, completeness, contract-version, and
    mismatch tests using persisted record fixtures
  - evidence: eligible exact match returns `reused_exact_match`; failed, blocked,
    incomplete, version-mismatched, fingerprint-mismatched, or fingerprintless
    candidates perform fresh evaluation and emit canonical reuse decision

- proof target: identity remains stable across URL changes
  - method: URL-drift, duplicate-URL, and minimal-input fixtures using existing
    `job_identity_keys`
  - evidence: raw fingerprint remains primary; URL fallback does not collapse
    distinct raw jobs or alter semantic fingerprint

- proof target: failure semantics are launch-path independent
  - method: inject failures in reranker resolution, fingerprint construction,
    reuse validation, evidence selection, and gap computation
  - evidence: every accepted per-job failure returns `analysis_failed` with
    canonical error and trace shape

- proof target: pipeline and stage runner are semantic-free callers
  - method: residue search and focused pipeline tests
  - evidence: no calls to CV-analysis evidence retrieval, fallback, gap, fit, or
    record-building helpers outside analyzer; pipeline tests assert call/output
    routing only

- proof target: old built-in and agentic branches collapse without semantic loss
  - method: pre-deletion parity fixtures followed by canonical-output assertions
  - evidence: same status, evidence-selection summary, gap, requirement coverage,
    `do_not_claim`, readiness, and error classification for identical inputs

- proof target: downstream consumers accept one record shape
  - method: CV-generation, worker, control-plane, stage-artifact, and observation
    tests using canonical record fixtures
  - evidence: no downstream hydration helper or local default synthesis is needed

- proof target: compatibility labels are observational only
  - method: run same fixtures with compatibility labels enabled and disabled
  - evidence: canonical record differs only in explicitly observational runtime
    metadata, if any

- proof target: Phase 1 batch behavior is non-asymptotic and serial
  - method: empty, single-item, and mixed-status pipeline fixtures
  - evidence: deterministic order, effective concurrency `1`, and identical
    canonical records regardless of configured concurrency value

- proof target: docs and generated stage contracts remain synchronized
  - method: `python tools/docs/generate_architecture_metadata.py --check` and repo
    contract validation
  - evidence: stage source, generated stage output, planning lifecycle, and doc
    contract validators pass

## Completion Criteria

A specification item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Phase 1 has no required child specs. It is complete when canonical owner,
residue, parity, downstream-consumer, and documentation proof targets pass.

Canonical source-of-truth:

<LINK>
- `docs/superpowers/specs/2026-07-14-12-13-fitcv-llm-runtime-spine-master-spec.md`
- `docs/stages/cv_analysis.source.yaml`
- `src/fitcv/agentic_cv_analysis.py`
- `src/fitcv/late_stage_contract.py`
- `scripts/validate_planning_lifecycle.py`
</LINK>

