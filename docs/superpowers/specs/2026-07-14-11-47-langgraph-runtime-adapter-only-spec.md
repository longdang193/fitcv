---
layer: change
artifact_type: spec
status: completed
template_id: detailed-specification
name: langgraph-runtime-adapter-only-late-stage-cv-generation
parent_thread: workstream-operator-control-plane.fitcv-cp-app-ssot-symmetry-refactor
targets:
  - src/fitcv/runtime_routing.py
  - src/fitcv/cv_generator.py
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_runner.py
  - src/fitcv/late_stage_contract.py
  - src/fitcv/tracker.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/worker_run_support.py
  - config/runtime/control_plane.yaml
  - docs/stages/cv_generation.source.yaml
  - docs/configuration.md
  - docs/pipeline.md
  - tests/test_cv_generator.py
  - tests/test_pipeline.py
  - tests/test_pipeline_agentic_late_stage.py
  - tests/test_cv_generation_reason_mapping.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_worker_job.py
related_features:
  - cv_system
  - settings_system
  - trigger_run_management
  - inspection_debugging
related_stages:
  - cv_analysis
  - cv_generation
---

# Detailed Spec: LangGraph as runtime adapter only for late-stage CV generation

## Goal

Collapse late-stage CV generation to one repo-native business entrypoint:

`fitcv.agentic_cv_generation.generate_from_analysis(...) -> CvGenerationResult`

Phase 1's canonical `CvAnalysisRecord` is sole semantic input authority. Generator consumes that record, applies one generation state machine, and emits one `CvGenerationResult` shape for every admissible analysis status, reuse outcome, provider outcome, validation outcome, repair outcome, review outcome, replay, and resume path.

LangGraph remains only behind a private writer-adapter seam. It may execute provider calls, transport retries, graph nodes, tools, and traces. It must not own prompt meaning, readiness, fingerprints, reuse eligibility, validation, repair policy, acceptance, persistence semantics, statuses, or result shape.

Phase 2 collapses `cv_generation` ownership. It does not extract Phase 3's shared cross-stage LLM runtime spine.

## Key Deliverables

### Deliverable 1: one canonical generation entrypoint

`generate_from_analysis` owns analysis passthrough, exact reuse, fresh generation, validation repair, acceptance, review-required, validation failure, and generation failure.

Canonical call shape:

```python
generate_from_analysis(
    analysis_record: CvAnalysisRecord,
    profile: dict[str, Any],
    config: dict[str, Any],
    *,
    reusable_record: dict[str, Any] | None = None,
) -> CvGenerationResult
```

Contract rules:

- `analysis_record` is Phase 1 canonical record, not a reconstructed job, evidence, fit, or gap bundle.
- `reusable_record` is at most one persisted candidate located by orchestration; generator owns fingerprint comparison, contract compatibility, completeness, reuse eligibility, current-policy validation, and rebinding.
- adapter selection remains private. Pipeline, worker, API, and control-plane callers never choose semantic method.
- direct, pipeline, stage-runner, worker, replay, and resume callers receive same result contract.
- no service class, factory, registry, or public adapter interface is introduced.

### Deliverable 2: one canonical `CvGenerationResult`

`CvGenerationResult` and one canonical result builder in `agentic_cv_generation.py` own output shape and status semantics.

Canonical field groups:

- identity: `raw_job_fingerprint`, `job_url`, `job_title`, `analysis_input_fingerprint`, `cv_generation_input_fingerprint`, `cv_generation_input_components`
- reuse: `cv_generation_reuse_status`, `reuse_decision`, `reused_cv_version_id`
- inherited decision context: `status`, `ranking_fit_label`, `fit_classification`, `decision_chain`, `analysis_input_summary`, `evidence_used`, `evidence_selection_summary`, `gap_summary`
- generation cycle: `structured_cv_initial`, `validation_initial`, `repair_attempt`, `structured_cv_final`, `markdown_final`, `validation`
- terminal explanation: `outcome_reason`, `error`, `review_required_reason_code`, `validation_evidence_fingerprint`
- runtime observation: `runtime_provenance`, `agentic_live_trace`

Normalized `runtime_provenance` requires `route_part`, `runtime_path`, `adapter`, `provider`, `model`, and `wire_api`. Trace/request IDs, latency, transport attempts, and graph/tool detail remain optional observation fields. Secrets and raw credentials never enter provenance.

Pipeline debug, observation, stage-artifact, API, and worker payloads are projections of this record. They may add run context, IDs, timestamps, or storage references, but may not reconstruct status, validation, repair, reuse, or artifact meaning.

### Deliverable 3: one status and transition contract

`late_stage_contract.py` remains sole status-vocabulary owner.

Analysis passthrough statuses:

- `blocked_by_reranker_fit`
- `skipped_fit_gate`
- `analysis_failed`

Generation terminal statuses:

- `accepted`
- `review_required`
- `validation_failed`
- `generation_failed`
- `persistence_failed`

Status rules:

- only `ready_for_generation` enters writer execution or exact generation reuse.
- non-ready analysis statuses return canonical passthrough results with no generated artifacts, validation, repair, or runtime invocation.
- `review_required` retains usable final artifacts but stage-owned policy requires human review; it is not persisted as an accepted CV version.
- `validation_failed` means output remains invalid after canonical bounded repair.
- `generation_failed` covers routing, provider, transport, parsing, normalization, or rendering failure before usable final result.
- `persistence_failed` is allowed only after `accepted` produced final artifacts and accepted-version persistence failed.
- one canonical result-status type covers analysis passthrough and all generation terminal statuses; local narrower literal unions are removed.
- expected analysis blocks/skips and review-required decisions use `outcome_reason`; unexpected generation, validation, and persistence failures use `error`.
- review-required results set `review_required_reason_code` and `validation_evidence_fingerprint`; their `outcome_reason` uses stage `review`, the same reason code, and a human-readable message.
- error payload shape is `stage`, `code`, and `message`; failure-stage taxonomy is `configuration`, `routing`, `provider`, `transport`, `parsing`, `normalization`, `rendering`, `validation`, and `persistence`.

### Deliverable 4: one private writer-adapter seam

Canonical generation builds one repo-native write request containing canonical prompt text and identity, canonical response schema, resolved routing snapshot, attempt kind, repair targets, and adapter-neutral trace metadata.

Private adapter returns raw structured payload or raw provider response, runtime provenance, optional trace payload, and transport telemetry.

LangGraph may own only provider client setup from resolved routing, graph sequencing, provider/tool invocation, transport retry/timeout execution, trace capture, and conversion to adapter-neutral raw response.

LangGraph may not own readiness, prompt/schema meaning, fingerprints, reuse, normalization, validation, semantic repair policy, acceptance, persistence, statuses, errors, result fields, or artifact shape.

Phase 2 retains the direct repo-native writer as a supported contract-equivalent adapter for built-in/offline routing. It consumes the same canonical request and returns the same adapter-neutral response as LangGraph. Phase 2 deletes duplicate semantics, not this supported transport path.

### Deliverable 5: one reuse and persistence boundary

Generator owns generation fingerprint and exact-reuse validity. Fingerprint includes current analysis fingerprint, prompt identity/version, template identity or content fingerprint, enabled sections, acceptance/validation policy, resolved output-affecting route fields, and generation contract version.

`agentic_late_stage_enabled`, `late_stage_mode`, trace settings, run ID, timestamps, latency, worker slot, and mutable job URL are not semantic fingerprint components.

One exported pure fingerprint builder in `agentic_cv_generation.py` is the SSOT for generation lookup keys. Pipeline calls it for batch candidate lookup; `generate_from_analysis` calls the same helper again before reuse. Pipeline or tracker may batch-locate candidates. Generator reuses only a matching, current-contract, reusable, complete candidate whose final structured CV and markdown pass current canonical validation. Invalid, stale, incomplete, mismatched, or failed candidates fall through to fresh generation in same invocation.

Persistence stays outside semantic writer execution. Pipeline persists only canonical `accepted` results. `review_required` artifacts remain observable but are not stored as accepted CV versions. On failure, pipeline calls a canonical generation transition helper that produces `persistence_failed`, preserves final artifacts and validation, and sets persistence-stage error. Pipeline does not build that shape locally.

## Uniform Semantic Flow

Every admissible invocation uses this skeleton:

1. validate trust-boundary input shape
2. interpret canonical analysis readiness
3. build canonical request, routing snapshot, and generation fingerprint
4. validate supplied exact-reuse candidate
5. invoke routed writer adapter only when reuse is unavailable
6. parse and normalize structured candidate
7. render candidate markdown
8. run canonical initial validation
9. decide and execute canonical bounded repair cycle
10. re-render repaired candidate and run final validation
11. apply acceptance versus review-required policy
12. build one canonical `CvGenerationResult`
13. let orchestration persist and emit projections

Non-ready analysis statuses stop after step 2 and still use same result builder. Valid exact reuse skips provider execution at step 5 but still runs current canonical validation. Persistence failure is post-generation transition after step 12, not alternate generation method.

## Trust Boundary and Failure Envelope

Programmer or trust-boundary violations may raise before per-job work: non-mapping profile/config, non-canonical analysis input, ready record missing required identity/job/evidence/gap fields, or invalid private adapter return type.

After valid per-job input enters generation, operational failures do not escape to pipeline as alternate semantic paths. Routing, provider, transport, parse, normalization, render, validation, and repair exhaustion become canonical results. Run cancellation and process interrupts remain orchestration exceptions.

## Task/Wave Breakdown

### Wave 1: Freeze parity and ownership fixtures

**Purpose:**
- capture current output behavior before deleting dual semantic methods

**Steps:**
- [x] inventory fields emitted by canonical generator, pipeline built-in path, debug records, observations, stored versions, API payloads, and worker payloads
- [x] freeze fixtures for all analysis passthrough and generation terminal statuses
- [x] freeze validation, repair success, repair exhaustion, review, exact reuse, provider failure, and persistence failure fixtures
- [x] identify adapter-only allowed differences

**Verification:**
- [x] fixture matrix separates required contract fields from branch-local telemetry and stale mode baggage

**Exit Criteria:**
- no field survives only because one duplicate branch emits it

### Wave 2: Complete canonical generator contract

**Purpose:**
- move missing meaning into one entrypoint and one result builder

**Steps:**
- [x] type `generate_from_analysis` against canonical `CvAnalysisRecord`
- [x] complete identity, fingerprint, reuse, validation, repair, artifact, error, and provenance fields in `CvGenerationResult`
- [x] move generation fingerprint construction out of `pipeline.py`
- [x] remove observational mode and mutable URL fields from semantic fingerprint
- [x] move exact-reuse validation and rebinding into generator boundary
- [x] make non-ready outcomes use same canonical result builder
- [x] move acceptance and review-required decision into generator boundary
- [x] add canonical persistence-failure transition helper

**Verification:**
- [x] direct generator tests cover every status and reuse path without pipeline semantic hydration

**Exit Criteria:**
- one function and one builder express every canonical generation outcome

### Wave 3: Demote LangGraph to private adapter

**Purpose:**
- preserve orchestration value while removing second meaning ownership

**Steps:**
- [x] build prompt, response schema, routing snapshot, and repair targets before adapter invocation
- [x] make LangGraph consume adapter-neutral request
- [x] make LangGraph return adapter-neutral raw response, provenance, and trace
- [x] move parse, normalize, render, validation, repair decision, acceptance, statuses, and result assembly outside graph-owned execution
- [x] retain direct writer only as contract-equivalent transition/fallback adapter when required by tested runtime behavior

**Verification:**
- [x] LangGraph and direct adapter fixtures normalize to same canonical result outside allowed telemetry differences

**Exit Criteria:**
- replacing LangGraph changes runtime mechanics only, not stage meaning

### Wave 4: Delete pipeline semantic ownership

**Purpose:**
- make pipeline, stage runner, worker, and API thin orchestration/projection callers

**Steps:**
- [x] delete `_run_non_agentic_cv_generation`
- [x] delete `_run_agentic_cv_generation`
- [x] delete mode-based routing preflight and compute branches
- [x] delete pipeline-local validation and repair orchestration
- [x] delete pipeline-local accepted, review-required, validation-failed, generation-failed, and persistence-failed result construction
- [x] retain scheduling, cancellation, candidate lookup, persistence, reporter emission, observation emission, and stage-boundary handling only
- [x] make projections consume canonical `CvGenerationResult`

**Verification:**
- [x] residue checks find no decision-critical branch on `agentic_late_stage_enabled` or `late_stage_mode`
- [x] pipeline and stage runner no longer import validators or repair policy for generation decisions

**Exit Criteria:**
- pipeline cannot select or reconstruct second CV-generation method

### Wave 5: Contract and stage-doc closeout

**Purpose:**
- align source, tests, runtime metadata, and docs with one owner

**Steps:**
- [x] update stage source and feature metadata for canonical owner wording
- [x] update configuration docs so mode labels are observational only
- [x] update pipeline docs for one generation state machine and routing owner
- [x] add parity, residue, replay/resume, worker, API, and persistence-boundary tests
- [x] run planning, repo-contract, architecture-metadata, focused test, typing, compilation, and diff checks required by touched surfaces

**Verification:**
- [x] docs and generated metadata expose no second semantic owner

**Exit Criteria:**
- Phase 2 is implementation-plan ready with executable proof targets

## Design Decisions

### Decision: keep `generate_from_analysis` as sole business entrypoint

- context: existing function already consumes analysis output and returns most complete repo-native generation result shape.
- choice: complete it instead of adding service, engine, or new public facade.
- alternatives considered: create `CvGenerationService`; move meaning into pipeline; make LangGraph graph state public contract.
- impact: smallest owner-collapse diff; direct tests remain useful; graph internals remain replaceable.

### Decision: Phase 1 `CvAnalysisRecord` is sole input authority

- context: pipeline currently unwraps job, evidence, gap, fit, and summaries, then passes parallel arguments through different methods.
- choice: generator derives inherited meaning from canonical analysis record and rejects missing required fields for ready records.
- alternatives considered: preserve parallel argument bundle; rebuild analysis meaning from job/profile.
- impact: `do_not_claim`, evidence, gap, and fit cannot drift after analysis; replay and resume use same boundary as fresh execution.

### Decision: adapter seam is private and callable-shaped

- context: Phase 2 has one real alternate orchestration technology but no need for public plugin framework.
- choice: use one private callable seam around writer execution. Add no one-implementation interface, factory, registry, or base class.
- alternatives considered: public `CvWriterAdapter` protocol and registry; LangGraph-specific public request/result types.
- impact: deterministic tests can inject runtime behavior; Phase 3 generalizes only proven repetition.

### Decision: canonical policy surrounds adapter invocation

- context: current LangGraph and pipeline built-in paths each perform parsing, validation, repair, acceptance, and result assembly.
- choice: adapter performs transport/orchestration only. Canonical generator owns work before and after every adapter call.
- alternatives considered: adapters return final stage results; preserve parity between two complete semantic paths.
- impact: adapter parity stays small; stage semantics cannot diverge by runtime family.

### Decision: reuse is semantic; lookup and persistence are orchestration

- context: pipeline builds fingerprints, trusts reusable rows, hydrates accepted results, and stores copied versions.
- choice: pipeline may locate and persist records; generator owns semantic fingerprint, reuse eligibility, current-policy validation, and reused result shape.
- alternatives considered: keep reuse entirely in pipeline; place storage queries inside generator.
- impact: reuse behaves uniformly across direct, pipeline, replay, and resume paths while generator remains storage-independent.

### Decision: persistence failure is post-generation status transition

- context: final artifacts can be valid while storage fails, so generation failure would lose truth.
- choice: retain `persistence_failed`; pipeline owns I/O and invokes one canonical transition helper on failure.
- alternatives considered: persist inside generator; report storage failure as `generation_failed`.
- impact: artifact truth remains; pipeline does not rebuild persistence meaning.

### Decision: mode labels are observational only

- context: `late_stage_mode` and `agentic_late_stage_enabled` remain in control-plane and trace payloads while pipeline still branches on them.
- choice: retain labels temporarily for compatibility, but never use them for fingerprint, readiness, runtime result meaning, validation, repair, acceptance, persistence, or status.
- alternatives considered: keep mode as semantic selector; delete every compatibility field in Phase 2.
- impact: branch collapse can precede consumer cleanup; identical inputs keep identical semantics.

### Decision: routing stays SSOT-owned outside LangGraph

- context: `runtime_routing.py` and `config/runtime/control_plane.yaml` already resolve provider, model, base URL, wire API, and timeout.
- choice: generator resolves routing once; adapter consumes snapshot. LangGraph env values remain compatibility transport and must match routed truth.
- alternatives considered: LangGraph env selects provider/model independently; duplicate route config inside graph package.
- impact: provider swaps remain stage-symmetric; drift checks remain meaningful.

## Invariants

- `generate_from_analysis` is sole per-job CV-generation business entrypoint.
- Phase 1 `CvAnalysisRecord` is sole inherited meaning source.
- `CvGenerationResult` and canonical result builder have one owner in `agentic_cv_generation.py`.
- `late_stage_contract.py` is sole status-vocabulary owner.
- only `ready_for_generation` may invoke writer adapter or exact generation reuse.
- blocked, skipped, and analysis-failed records never invoke provider, validate, repair, render, persist, or emit generated artifacts.
- every ready record follows same parse, normalize, render, validate, repair, final-validate, and decision policy regardless of adapter.
- adapter choice cannot change status meaning, fingerprint, validation fields, repair fields, acceptance policy, or artifact shape.
- valid exact reuse skips provider execution but passes current canonical validation and result construction.
- runtime routing resolves once from `runtime_routing.py` and `config/runtime/control_plane.yaml`.
- LangGraph consumes resolved routing; it never resolves independent semantic routing truth.
- `agentic_late_stage_enabled` and `late_stage_mode` are absent from semantic fingerprints and decision branches.
- expected blocks/skips use `outcome_reason`; failures use `error`.
- `review_required` retains usable final structured CV, markdown, validation, review reason code, and validation evidence fingerprint, but is not persisted as an accepted CV version.
- `persistence_failed` retains usable accepted final artifacts and prior validation.
- validation or generation failure never persists a CV version.
- pipeline may schedule, cancel, locate candidates, persist, and emit projections; it may not validate, repair, accept, or build status meaning.
- direct, pipeline, stage-runner, worker, replay, and resume paths return semantically identical results for identical deterministic inputs.
- adapter-local trace richness cannot change acceptance semantics.

## Adapter-Invariant and Allowed-Difference Sets

Must be equal after deterministic normalization:

- analysis and generation input fingerprints
- status and decision chain
- reuse decision and reuse status
- evidence, evidence-selection summary, gap, and `do_not_claim` grounding
- initial and final structured CV for deterministic fixtures
- validation field names and semantic contents
- repair performed flag, targets, reason, and bounded attempt count
- final markdown semantic content
- outcome reason or error stage/code classification
- accepted, review-required, and persistence eligibility

May differ without breaking symmetry:

- adapter name and runtime path
- provider and model when route intentionally differs
- provider request ID, trace ID, span ID, and tool-call ID
- latency and timestamps
- transport retry count
- raw provider response metadata
- adapter-local node/tool trace detail

No allowed difference may feed back into status, validation, repair, acceptance, reuse, persistence eligibility, or artifact semantics.

## Acceptance Criteria

- Phase 1 canonical `CvAnalysisRecord` is direct input to one `generate_from_analysis` business entrypoint.
- One canonical result builder emits all passthrough, reuse, generation, validation, review, and persistence-failure shapes.
- `pipeline.py` contains no `_run_non_agentic_cv_generation` or `_run_agentic_cv_generation` semantic methods.
- Pipeline contains no decision-critical branch on `agentic_late_stage_enabled` or `late_stage_mode`.
- LangGraph consumes canonical writer request and returns adapter-neutral raw response plus runtime observation only.
- Prompt building, parsing, normalization, rendering, validation, repair policy, acceptance, statuses, and result assembly remain repo-native.
- Generation fingerprint excludes observational mode labels and mutable job URL.
- Generator validates and rebinds reusable candidates; invalid candidates fall through to fresh generation in same invocation.
- Review-required output is not persisted as an accepted CV version. Accepted persistence failure preserves final artifacts and uses canonical transition helper, not pipeline-local result construction.
- Deterministic adapter parity tests pass for every proof-matrix row after only allowed telemetry fields are normalized.
- Pipeline, stage-runner, worker, API, replay, and resume tests consume canonical result without semantic hydration.
- Stage and configuration docs describe one generation contract and one routing owner.
- Residue tests fail if second mode-owned semantic method returns.

## Proof Matrix

| Case | Adapter call | Repair | Final status | Final artifacts |
|---|---:|---:|---|---|
| reranker block passthrough | no | no | `blocked_by_reranker_fit` | absent |
| fit-gate skip passthrough | no | no | `skipped_fit_gate` | absent |
| analysis failure passthrough | no | no | `analysis_failed` | absent |
| valid exact reuse | no; yes after rejection | no unless fresh output needs repair | `accepted` or `review_required` | present |
| stale or invalid reuse candidate | yes | policy-driven | canonical fresh outcome | outcome-driven |
| initial output valid | yes | no | `accepted` or `review_required` | present |
| candidate-name repair succeeds | yes | yes | `accepted` or `review_required` | present |
| missing-section repair succeeds | yes | yes | `accepted` or `review_required` | present |
| repair exhausted | yes | yes | `validation_failed` | no accepted final artifact |
| routing/provider/transport failure | yes | transport retry only | `generation_failed` | absent |
| parse/normalize/render failure | yes | no or policy-driven | `generation_failed` | absent |
| accepted persistence fails | already complete | already complete | `persistence_failed` | preserved |

## Non-Goals

- redesigning Phase 1 CV-analysis evidence, gap, fit, reuse, or status policy
- extracting Phase 3 shared LLM request/parse/provenance/error framework
- migrating enrichment or ranking in Phase 2
- changing business validation, repair, acceptance, or review thresholds except where owner collapse requires one existing rule
- forcing deterministic helpers into LangGraph nodes
- introducing public adapter registry, plugin system, service class, or factory
- renaming `agentic_cv_generation.py` solely for aesthetics
- removing all compatibility mode fields from API/UI payloads in same phase
- moving tracker or SQLite I/O into semantic generator
- writing Phase 2 implementation plan before this spec passes review

## Risks and Mitigations

- Risk: current built-in and LangGraph paths hide meaningful output differences.
  - mitigation: freeze proof-matrix fixtures first; preserve explicit contract behavior, not branch placement.
- Risk: moving validation around adapter changes markdown-sensitive behavior.
  - mitigation: preserve canonical render-before-validation order for each initial and repaired structured candidate.
- Risk: exact reuse bypasses current validation or accepts stale policy output.
  - mitigation: validate fingerprint, contract version, completeness, eligibility, and current policy before reuse acceptance.
- Risk: pipeline still hydrates missing fields and remains shadow owner.
  - mitigation: require complete canonical results and add residue tests for local builders and status literals.
- Risk: LangGraph trace/tool behavior is lost during demotion.
  - mitigation: retain adapter-local telemetry and test observation projection separately from stage meaning.
- Risk: persistence failure collapses into generation failure.
  - mitigation: keep explicit canonical post-generation transition preserving final artifacts.
- Risk: mode field remains in generation fingerprint and blocks symmetry.
  - mitigation: bump fingerprint schema and prove label toggles do not change semantic fingerprint or result.
- Risk: trust-boundary exceptions crash whole batch.
  - mitigation: keep programmer/input-contract raises before valid per-job envelope; convert operational failures to canonical records after entry.

## Validation Plan

- proof target: one generation owner exists
  - method: source inspection and residue grep
  - evidence: one `generate_from_analysis` business entrypoint and no pipeline non-agentic/agentic semantic helpers

- proof target: Phase 1 analysis record remains sole input authority
  - method: direct, pipeline, replay, and resume tests
  - evidence: generation does not recompute evidence, gap, fit, or `do_not_claim` from job/profile when canonical record exists

- proof target: LangGraph is adapter-only
  - method: private adapter fixture tests and source inspection
  - evidence: graph code invokes runtime and captures traces only; canonical code parses, normalizes, renders, validates, repairs, decides, and builds

- proof target: statuses and result shape are canonical
  - method: proof-matrix contract tests
  - evidence: every row emits expected status, artifact presence, validation, repair, outcome/error, and provenance field set

- proof target: adapter outputs are semantically symmetric
  - method: deterministic direct-versus-LangGraph adapter comparison
  - evidence: adapter-invariant fields are equal after normalizing only allowed telemetry differences

- proof target: generation reuse is current and symmetric
  - method: exact, stale, incomplete, invalid, mode-toggle, prompt-change, policy-change, and route-change tests
  - evidence: only exact current candidates reuse; all others fresh-compute under same canonical flow

- proof target: persistence boundary preserves truth
  - method: successful persistence and forced persistence-failure tests
  - evidence: only accepted/review results persist; failure preserves final artifacts and uses canonical persistence transition

- proof target: orchestration surfaces are thin projections
  - method: pipeline, stage-runner, worker, API, observation, and stage-artifact tests
  - evidence: projections match canonical result and add no local semantic fields

- proof target: mode compatibility is observational only
  - method: toggle tests and fingerprint comparison
  - evidence: `agentic_late_stage_enabled` and `late_stage_mode` do not change fingerprint, status, validation, repair, acceptance, or artifacts

- proof target: deleted semantic owners stay deleted
  - method: residue assertions
  - evidence: no `_run_non_agentic_cv_generation`, `_run_agentic_cv_generation`, pipeline-local generation fingerprint builder, or decision-critical mode branch remains

- proof target: repository documentation lifecycle remains valid
  - method: planning lineage, planning lifecycle, repo contracts, architecture metadata, compilation, focused tests, typing, and diff checks required by touched files
  - evidence: required validators pass; unrelated pre-existing failures are recorded separately

## Completion Criteria

A specification item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

For this Phase 2 spec, implementation plan becomes downstream child once planning begins. Spec remains `active` until implementation and verification close all acceptance criteria.

Canonical source-of-truth:

<LINK>
- `C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\docs\superpowers\specs\2026-07-14-12-13-fitcv-llm-runtime-spine-master-spec.md`
- `C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\docs\operating_system\governance\repo-governance.md`
- `C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\scripts\validate_planning_lifecycle.py`
</LINK>
