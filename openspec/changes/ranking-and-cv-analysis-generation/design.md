# Design

## Context

See `proposal.md` and the two capability specs for the behavioral contract. The current pipeline already has stage checkpoints, candidate evidence projections, ranking orchestration, CV analysis/generation modules, a native PDF path, and persisted artifacts. `src/fitcv/ranking.py` currently performs personalized ordering when an active preference policy is available, and `decision-learning-v2` remains an active policy version. Those fields and policy inputs are therefore active behavior for existing runs, not merely historical compatibility data. `config/policy/cv.yaml` currently selects `europass`, while `src/fitcv/cv_presets.py` and `src/fitcv/cv_generator.py` own the current preset and PDF boundaries.

The FigJam flow places Ranking before the final Top 15 CV handoff. Ranking input is bounded by the existing 12,000-character contract. CV generation then performs evidence planning, fixed-template creation, initial ATS/achievement/impact optimization, unified validation, a bounded correction/revalidation loop, deterministic `mycvs_v1` Markdown rendering, mandatory PDF conversion, one-page render acceptance, and independent review/PDF outcomes.

## Goals / Non-Goals

**Goals:**

- Make new ranking decisions and their handoff versioned, reproducible, and evidence-backed.
- Reuse existing evidence, stage, checkpoint, and persistence boundaries.
- Add deterministic `mycvs_v1` rendering/validation without making converter details implicit. The visible output follows the maintained candidate format: contact/Iconify metadata, then `Summary`, `Education`, `Experience`, `Projects`, `Certificates`, and `Skills`; audit fields remain in a deterministic HTML comment outside the visible headings.
- Preserve the existing one-page render acceptance and make submission clearance explicit.
- Preserve historical artifacts and a rollback-safe migration path.

**Non-Goals:**

- Rewriting profile ingestion, shortlist admission, or downstream fit truth.
- Adding a new model provider, search service, database, or general-purpose workflow engine.
- Deleting or backfilling historic personalized ranking or Europass artifacts.
- Allowing a weighted mega-score to replace the documented core/Pareto policy.

## Implementation Boundaries

- Ranking computation and score-state normalization remain in `src/fitcv/ranking.py::rank_jobs` and `src/fitcv/ranking_contract.py`; the new order/version envelope must extend those seams rather than introduce a parallel ranking path.
- Ranking-stage serialization remains owned by `src/fitcv/pipeline_stage_artifacts.py::build_ranking_stage_block`. Run/checkpoint persistence and resume compatibility remain owned by `src/fitcv_cp/models.py`, `src/fitcv_cp/sqlite_store.py`, and `src/fitcv_cp/worker_job.py`.
- The immutable ranking-to-CV handoff is produced from the admitted shortlist and persisted inside `stage_transition_artifacts_json.stages.ranking`; CV analysis and generation consume it through `src/fitcv/agentic_cv_analysis.py`, `src/fitcv/agentic_cv_generation.py`, and the existing worker boundary in `src/fitcv_cp/worker_job.py`.
- CV rendering and render-proof compatibility remain in `src/fitcv/cv_generator.py` and `src/fitcv_cp/run_artifact_contracts.py`. The new adapter may add the smallest reusable serializer/adapter seam required by those owners, but must not duplicate final-artifact acceptance logic.
- `config/policy/cv.yaml` remains the configuration owner. Additive renderer configuration must preserve `cv.preset: europass` and its existing default behavior; no new provider, database, or workflow engine is required.
- Tests extend the existing ownership boundaries: `tests/test_ranking.py`, `tests/test_ranking_contract.py`, `tests/test_pipeline_checkpoint_contract.py`, `tests/test_pipeline_stage_resume_parity.py`, `tests/test_cv_generator.py`, `tests/test_cv_render_acceptance.py`, `tests/test_fitcv_cp/test_run_artifact_contracts.py`, `tests/test_fitcv_cp/test_worker_job.py`, and `tests/test_fitcv_cp/test_sqlite_store.py`.

## Decisions

### 1. Version ranking order before retiring personalization

The ranking stage writes one versioned decision envelope containing `ranking_order_version`, the active ranking-policy version, and their provenance. The current personalized order remains authoritative for runs whose persisted order version uses it; a new order version may retire personalization and make the AI compatibility/tie-break order authoritative. A resumed run SHALL use the persisted order and policy versions rather than current defaults, and a strategy change SHALL require a new run/checkpoint identity. Historic personalized fields remain readable in either case.

**Alternative rejected:** removing legacy fields immediately, because historic operator views and persisted artifacts depend on them.

### 2. Use explicit result states instead of score coercion

Missing, invalid, and retryable evaluations remain typed outcomes. The existing three-value `score_status` contract (`valid`, `unscored`, `invalid`) remains unchanged. Retryability is represented by the existing `failure_code`, `disposition=retryable_failure`, and `retry_eligible` fields; it SHALL NOT become a fourth score status. The ranking adapter must not convert failures to `0.0`, because that conflates technical failure, uncertainty, and confirmed incompatibility.

**Alternative rejected:** zero-filling invalid scores for simpler sorting; it damages auditability and hides retryable failures.

### 3. Make the ranking-to-CV handoff immutable and provenance-rich

Persist a handoff object containing job qualifiers, baseline ranking data, evidence IDs, gaps, profile revision, ranking order/policy and score contract versions, and a fingerprint. The handoff SHALL be stored in the persisted ranking stage artifact under `stage_transition_artifacts_json.stages.ranking`, with per-job references retained in the ranking/admission ledger where available. CV analysis consumes this object rather than reconstructing ranking context from mutable source tables.

The handoff fingerprint SHALL use version `ranking_cv_handoff_v1` and SHA-256 over canonical UTF-8 JSON serialized with lexicographically sorted object keys and compact separators (`(',', ':')`, `ensure_ascii=false`). Its input object SHALL contain exactly the canonical job identity and qualifiers, baseline rank and score, `score_status`, `failure_code`, `disposition`, `retry_eligible`, ordered evidence IDs, confirmed gaps/unknowns, candidate profile revision, ranking order version, ranking policy/contract versions, and source provenance references. Optional absent values SHALL be encoded as JSON `null`, not omitted; strings SHALL use the field's normalized value; arrays SHALL use the contract-defined deterministic order. The schema version is part of the hashed object.

**Alternative rejected:** passing only job ID and score; it cannot reproduce the exact decision or explain qualifier-sensitive CV changes.

### 4. Keep CV quality dimensions separate

Analysis, generation, review, PDF, and submission clearance are separate state transitions. Existing persisted/public lifecycle values remain authoritative: `generation_status` uses `pending|running|generated|review_required|validation_failed|generation_failed|persistence_failed|cancelled`, and the canonical review state uses `none|stretch|manual_required|approved|rejected`. A new additive `pdf_status` may use `pending|generated|failed`, and a new additive submission-clearance field may use `blocked|eligible`; neither replaces the existing fields. `generated` is the successful generation state; generic `completed` maps to it only in a new read model, and generic `failed` maps to the specific existing failure state. `none` or explicit `approved` review state clears the review gate; `stretch`, `manual_required`, and `rejected` do not. Hard factual/provenance/schema/template checks and one-page render acceptance gate completion; ATS/recruiter quality is an optimization signal unless policy marks it material. Soft factual concerns may require review and still permit conversion; hard validation failures prevent conversion.

**Alternative rejected:** one combined `cv_status`; it cannot represent a valid Markdown artifact with a failed converter or a review-required CV whose PDF was successfully generated.

### 5. Treat `myCVs` conversion as an external, pinned boundary

Render and validate exact `mycvs_v1` Markdown as defined by `schemas/mycvs_v1.md` before conversion. The external adapter SHALL emit the existing render-proof shape: `render_status`, `page_count`, `page_fit_status`, `artifact_checksum`, `content_sha256`, `template_sha256`, `render_config_fingerprint`, and a registered `renderer_contract_version`. The initial registered external value is `mycvs_external_render_v1`; the existing final-artifact predicate SHALL recognize it before the path can be accepted. Record converter commit/revision, stylesheet/template revision, input checksum, and conditional output checksum in the artifact provenance. Do not promote the path until the adapter, renderer contract, and all inputs are pinned and reproducible.

**Alternative rejected:** silently using the current external converter; it makes PDFs non-reproducible and prevents trustworthy release evidence.

### 6. Make `mycvs_v1` a renderer strategy, not a new preset

`config/policy/cv.yaml` remains the configuration owner. Preserve `cv.preset: europass` and its existing composition/artifacts; introduce an additive renderer strategy key for the new output path, with `mycvs_v1` selecting the deterministic serializer and external adapter. The strategy consumes the canonical intermediate CV model and does not change the meaning of the existing Europass preset. New writes use the renderer strategy only behind its explicit gate; reads and resumes use the persisted preset, renderer strategy, schema, and contract versions.

### 7. Roll out additively and keep shortlist ownership separate

Read paths accept both historic and new artifact shapes. New writes use the versioned contract behind an explicit strategy/configuration gate. Resume uses the persisted strategy and contract versions rather than current defaults. Rollback changes the active strategy, not historic artifacts.

Pareto admission and promotion remain owned by the shortlist capability through `pipeline.shortlist_strategy`. This ranking change consumes the admitted shortlist and SHALL NOT promote, override, or duplicate shortlist strategy gates. Any future ranking-strategy promotion must introduce a separately named ranking strategy and its own contract.

**Alternative rejected:** destructive migration or blanket rewrite of old artifacts.

## Risks / Trade-offs

- [Legacy readers depend on personalized fields] → Keep fields and label them historic; add compatibility tests before changing readers.
- [Non-deterministic model output] → Persist model/provider/settings, prompt/template revision, normalized inputs, timestamps, and final fingerprints; treat exact replay as an evaluation gate.
- [Converter drift or unavailable external tooling] → Pin revision/template/checksums and keep the existing safe PDF path until validated.
- [Review-required output may be mistaken for success] → Store independent review, PDF, and submission-clearance states; block submission until review is explicitly cleared.
- [One correction pass may leave quality gaps] → Preserve unresolved concerns and surface them for operator review rather than adding unbounded retries.

## Migration Plan

1. Add the two capability contracts and compatibility readers without changing the current production default or active personalized order for existing checkpoints.
2. Implement versioned ranking decision envelopes and the immutable CV handoff, including `ranking_cv_handoff_v1` fingerprinting and persisted order/policy versions.
3. Add `mycvs_v1` rendering/validation and the registered external render-proof adapter while retaining the current safe Europass preset/path.
4. Run shadow/replay and representative real-file probes; compare deterministic outputs and failure states.
5. Pin the converter commit/template/checksum policy, verify the adapter emits accepted render proof, and obtain release evidence.
6. Enable a new ranking order or CV renderer strategy only after its gates pass; otherwise retain the current strategy and record the blocker.

## Release Gates

- The exact external `myCVs` converter commit and stylesheet/template revision are an enablement gate, not an architectural choice. Implementation may ship the adapter and disabled configuration path with deterministic contract fixtures; production activation of `mycvs_external_render_v1` requires a release record containing the pinned converter revision, stylesheet/template revision, input/output checksum policy, and reproducibility evidence.
- Until that release record exists and the render-proof acceptance tests pass, retain the current safe Europass/native path and report the external path as not release-ready.
