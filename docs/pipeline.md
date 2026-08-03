---
doc_id: pipeline
doc_type: architecture-guide
explains:
  stages:
    - cv_analysis
    - cv_generation
    - enrich
    - normalize
    - ranking
    - rule_filter
    - shortlist
---

# Pipeline

Stage order:

`normalize -> enrich -> rule_filter -> shortlist -> ranking -> cv_analysis -> cv_generation`

This page is a cross-cutting summary of runtime behavior and ownership.

Input jobs contract and normalization: [job-data-input.md](job-data-input.md).

## Stage Responsibilities

- `normalize`: canonicalize incoming jobs and preserve provider-native `source_location` evidence
- `enrich`: derive structured job fields, canonical `actual_location`, canonical `language_requirements`, and reuse-aware metadata
- `rule_filter`: evaluate symmetric location/language factors, project policy modes, and apply deterministic gating before expensive steps
- `shortlist`: deterministic cosine retrieval over eligible jobs with valid embeddings; production rows use real vector evidence only
- `ranking`: authoritative fit scoring and decision labels
- `cv_analysis`: one canonical per-job analyzer owns evidence selection, gap, fit-gate, reuse validity, and generation readiness; pipeline owns batch invocation, persistence, and observations
- `cv_generation`: one canonical `generate_from_analysis` contract owns fingerprints, reuse validity, structured generation, validation, repair, acceptance/review meaning, and result shape; pipeline persists canonical `accepted` results only

Shared LLM runtime rule: `enrich`, `ranking`, `cv_generation`, and auxiliary synonym triage build owner-local prompts and parse owner-local outputs through `src/fitcv/llm_runtime.py`. Shared runtime owns routing, credentials, transport, wire fallback, normalized operational failures, provenance, and the only persistable per-call evidence projection. Embeddings and deterministic builtin synonym triage remain outside this generative spine.

## Candidate Evidence Projection

CV analysis converges every immutable Candidate Profile revision before retrieval:

`candidate-profile.v1 | candidate-profile.v2 -> validated v2 runtime snapshot -> candidate-evidence.v1 -> global selection`

- v1 adaptation happens in memory with deterministic IDs and source metadata; stored revision bytes and checksum remain unchanged
- legacy year-only ranges become deterministic month boundaries (`YYYY-01` for starts, `YYYY-12` for ends)
- experience, education, projects, achievements, certifications, and volunteering use one nested-evidence projector
- each nested evidence statement emits one item; section and kind remain provenance metadata, never score bonuses or reserved quotas
- derived claims link by `evidence_refs`; runtime reverses those links into evidence-item skills without duplicating ownership
- one global selection budget applies after channel retrieval and deterministic evidence-ID tie breaking
- analysis metadata records `source_profile_schema_version`, `projection_schema_version`, and `projection_fingerprint`
- traceability resolves `claim -> evidence_refs -> candidate-evidence.v1 item -> source_refs -> uploaded source document`

## Location And Language Eligibility

Phase 1 uses one path for both factors:

`raw evidence -> canonical fact -> evaluator truth -> absolute normalizer -> policy projection`

- provider adapters preserve source geography at ingest boundaries
- `location_type` remains work mode; `actual_location` remains geography
- job-language requirements remain distinct from skill entities
- candidate profile adaptation occurs once before factor evaluation
- every passed or rejected enriched row carries the same eligibility payload and policy fingerprint
- hard gates run before shortlist and ranking inputs are built
- only confirmed `gate_required` failures reject; unknown evidence stays eligible
- Phase 3 consumes these factor values without changing their absolute normalization or eligibility truth

## Vector-Only Shortlist

Phase 2 uses one path:

`eligible jobs -> valid cosine evidence -> total vector order -> production Top N`

- ordering is `vector_similarity` descending, then `job_url` ascending
- one latest embedding row per job URL is selected by `created_at DESC, id DESC`
- no synthetic shortlist backfill exists; production can contain fewer than configured Top N
- `raw_shortlist` remains checkpoint compatibility name for production retrieval rows
- `shortlist_diagnostics` preserves coverage and cutoff metrics in checkpoint state
- deterministic below-cutoff audit rows exist only in `stage_transition_artifacts.stages.shortlist.audit_sample`
- audit rows never reach shortlist persistence, AI scoring, ranking, exports, or `strong | stretch | skip` labels
- continuation preserves prior completed shortlist artifact block, including audit evidence, while current execution updates only stages in its execution segment

## Ranking-V2 Fixed Baseline

Phase 3 uses one path for every admissible scored job:

`holistic AI scalar + six absolute structured factors -> structured_fit -> baseline_fit -> baseline_fit_label -> global baseline_rank -> bounded preference residual -> personalized_rank -> top-N`

- `config/policy/ranking.yaml` owns one exact, versioned policy; production accepts only `holistic_ai_only`
- AI scoring emits `ai_score` plus diagnostics; model-authored labels have no ranking authority
- `holistic_ai_fit` is the bounded AI scalar and sole active baseline contribution
- six structured factors remain independently normalized, weighted, persisted, and observable
- hard-gated or disabled location/language factors are removed once from effective structured weights, then retained weights renormalize once
- missing factor inputs use globally stable policy defaults, never cohort statistics
- ordering is `baseline_fit DESC`, `raw_job_fingerprint ASC`, then `job_url ASC`
- vector similarity/rank remain shortlist evidence and never affect baseline score, label, fingerprint, or tie order
- canonical ranking rows use `baseline_fit`, `baseline_fit_label`, `baseline_rank`, factor records, policy versions, and `ranking_contract_fingerprint`
- personalized fields add raw/display score, residual, clipping flag, `personalized_rank`, and policy fingerprints; they never replace baseline facts
- checkpoint schema remains v1; centralized adapters read old ranking aliases and reject canonical/legacy conflicts
- stage-transition artifacts use v8 and preserve full-run/resume parity
- CV analysis consumes persisted baseline truth only; gap findings, vector evidence, and AI diagnostics do not override ranking qualification

## Execution Modes

- full run (`Run All`)
- checkpointed run (`Stage by Stage`)

Mode changes pacing, not stage truth semantics.

## Contracts and Evidence

- stage outcomes are stage-owned truth
- operator summaries are derived views
- run artifacts/events must remain consistent with stage-owned outcomes
- `StageResult`/trace fields and run exports are the audit surface

## Two-Layer Observability Ownership

Observability separates run-level and item-level surfaces:

- **run-summary layer**
  - run-level events and summaries remain operator entrypoint surfaces
  - aggregate completion/debug surfaces describe run-wide behavior
- **item-observation layer**
  - item-level analysis/generation traces capture one candidate-job attempt at a time
  - item observations carry reviewer-facing input/output plus structured metadata for filtering

Ownership rule:

- run-summary surfaces answer **how run behaved overall**
- item observations answer **what happened for one candidate-job attempt**
- avoid duplicating full item raw IO into aggregate run-summary payloads

## Portability Expectations

- sqlite backend must preserve operator-visible contracts
- provider/model routing must be config/env controlled, not hardcoded

## Symmetry and Invariance Rules

- AI-stage decisions are backend-invariant: the same input must resolve the same routed AI provider/model regardless of SQLite file location or startup surface.
- Backend differences are persistence-only: storage schema/adapter metadata may differ, but AI decision logic, runtime evidence, stage traces, and provenance semantics remain equivalent.
- Fresh calls emit ordered `llm_runtime_observations`; reuse, replay, resume, blocked, and skipped cases emit zero new evidence.
- The runtime must treat `control_plane.model_routing.parts.*` as authoritative for AI stage provider/model selection.
- Historical late-stage mode fields are read-only compatibility data and never override unified routing or stage meaning.
- Location and language use the same factor result envelope and policy projection table for all admissible statuses and modes.
- Eligibility normalization is policy-versioned and run-cohort independent; filtered jobs cannot change surviving jobs' normalized values.
- Full-run and stage-resume paths build candidate fit context once and preserve identical eligibility payloads.
- Baseline normalization is absolute and cohort-independent; changing Top-N, unrelated rows, or input order cannot change a surviving job's score or label.
- Full-run, checkpoint resume, app replay, worker replay, exports, and CV analysis consume the same ranking contract fingerprint and canonical baseline fields.

## AI Credential and Error Contract

- Sole repo-native AI credential input: `FITCV_LLM_API_KEY`.
- Internal runtime uses `FITCV_LLM_API_KEY` without credential aliases or alternate provider clients.

Fail-fast guarantees:

- missing routed AI model/provider -> explicit runtime configuration failure
- missing AI API key for routed provider -> explicit runtime credential failure
- no hidden fallback to legacy provider defaults in unified runtime path

## Related Docs

- [architecture.md](architecture.md)
- [usage.md](usage.md)
- [FitCV-pipeline.md](FitCV-pipeline.md)


## Phase 4 Decision Feedback

1. Vector search emits each production row with normalized job embedding, vector fingerprint, and embedding-contract fingerprint.
2. Scoring requires a one-to-one URL match, then propagates evidence with the job raw fingerprint.
3. Completed-run export builds `decision_feedback_source_v1` from every evidence-complete production scoring row, including scored-not-ranked rows.
4. Native 1–5 forms append `set_rating` or `clear_rating` events without changing ranking, fit labels, CV eligibility, or application history.
5. Effective ratings use SQLite `event_sequence`; timestamps and UUIDs remain audit metadata only.
6. Phase 5 reduces complete event snapshots through the shared reducer and compiles rated pairs into deterministic weighted edges; no database edge table or ranking effect exists.
7. Phase 6 replays one compatible episode cohort offline, solves one bounded latent residual from zero with optional CVXPY + CLARABEL, and evaluates by held-out episode. It emits typed artifacts only and cannot change runtime ranking, labels, CV eligibility, or application history.
8. Phase 7 verifies current persisted evidence, applies one symmetric promotion gate against zero baseline and compatible parent, suppresses equivalent vectors, and stores immutable candidate/training records.
9. Manual activation changes one SQLite active snapshot. Each new run resolves once before ranking and freezes that payload in checkpoint state; resume never re-resolves. Personalized order may move jobs across top-N, while baseline `strong|stretch|skip`, CV analysis eligibility, and generation gates remain unchanged.
