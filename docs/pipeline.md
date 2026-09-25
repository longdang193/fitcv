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
- required-skill support is derived separately from profile fit: `profile_match` comes from `compute_gap()`, `canonical` records support across the projected evidence pool, `pool` records support after channel retrieval and merge, and `selected` comes only from final selected evidence; each map points requirement IDs to evidence IDs
- only selected `verified` support can produce `support_strength: supported`; `relevant_unverified`, `not_selected`, and `unsupported` stay non-authoritative
- `requirement_coverage` is the sole requirement-support authority; `supporting_evidence_ids` and `source_refs` point to selected `candidate-evidence.v1` items only
- analysis metadata records `source_profile_schema_version`, `projection_schema_version`, and `projection_fingerprint`
- traceability resolves `claim -> evidence_refs -> candidate-evidence.v1 item -> source_refs -> uploaded source document`

### CV-analysis Retrieval Diagnostics

- `cv_analysis.semantic_alignment.enabled` controls CV-analysis channel scoring only; it does not change shortlist embedding behavior
- when enabled, diagnostics identify `sqlite_deterministic_local` as the actual embedding backend, report dimension and contract fingerprint, and preserve configured model name as metadata
- the configured `cv_analysis.semantic_alignment.model` value does not prove provider execution; `generate_embedding()` remains deterministic local/hash output in this path
- when disabled, diagnostics report no semantic backend and channel scoring is lexical-only
- offline comparison uses `scripts/benchmark_requirement_support.py` with the fixed fixture at `tests/fixtures/requirement_support_benchmark.json`; it measures canonical, retrieved, selected, validation, timing, and context-cost boundaries without changing production defaults

### Requirement-support impact benchmark

- `evaluation_schema_version: 1` fixtures keep approved requirement–evidence pairs, unsupported requirements, validation cases, and scenario IDs in one source of truth
- requirement recall counts requirements with at least one valid approved supporter; evidence-pair recall counts approved requirement–evidence pairs; alternative-pair loss does not trigger pool expansion when requirement recall remains complete
- four offline arms answer separate questions: `lexical-baseline` is conventional lexical top-k, `lexical-ablation` disables requirement gain while retaining FitCV selection terms, `lexical-requirement-aware` is FitCV lexical selection, and `current-hash` enables current hash-based channels
- per-scenario reports include micro and macro coverage, retrieval-to-selection loss, explicit-link precision, selected item count, prompt cost estimates, and validation case results; zero-support scenarios use `not_applicable`
- benchmark validation consumes `analyze_ranked_job()` `requirement_coverage` and passes it unchanged to `run_all_validations()`; simplified support rows are not valid benchmark evidence
- CI smoke runs use `--runs 5 --warmups 1`; local comparisons use `--runs 50 --warmups 5`
- `generation_prompt_build_ms` measures `build_generation_prompt()`; `benchmark_payload_serialization_ms` is reported separately; prompt bytes and estimated tokens are local estimates, not provider usage
- historical comparison uses `scripts/benchmark_requirement_support_legacy.py` at `7263fba` and `scripts/compare_requirement_support.py`; historical validation semantics are reported as not comparable rather than inferred

Full-profile versus RAG impact measurement uses `tests/fixtures/rag_impact_benchmark.json`.
The fixture freezes one approved profile, development/pilot/held-out job splits,
requirement-to-evidence labels, claim-review policy, thresholds, and a profile
fingerprint. `scripts/evaluate_requirement_support_live.py:build_paired_inputs`
calls `analyze_ranked_job()` for the FitCV arm, projects selected evidence into
arm-authorized profile context, and builds both prompts from the same job. It
does not accept manually authored prompts when fixture-driven pairing is used.

Requirement coverage counts only answerable requirements with approved evidence
IDs. Factual precision counts reviewed factual claims; unreviewed claim
candidates remain in the review queue and stay out of the precision denominator.
Provider failures remain in attempted-call and accepted-CV denominators. Missing
cost telemetry reports unavailable cost without discarding quality or token
metrics. Generation-input tokens, total generation tokens, and total workflow
tokens remain separate scopes.

Example local probes:

```powershell
uv run python scripts/benchmark_requirement_support.py --arm lexical-baseline --runs 50 --warmups 5 --output .tmp/impact-lexical-baseline.json
uv run python scripts/benchmark_requirement_support.py --arm lexical-ablation --runs 50 --warmups 5 --output .tmp/impact-lexical-ablation.json
uv run python scripts/benchmark_requirement_support.py --arm lexical-requirement-aware --runs 50 --warmups 5 --output .tmp/impact-fitcv.json
uv run python scripts/benchmark_requirement_support.py --arm current-hash --runs 50 --warmups 5 --output .tmp/impact-current-hash.json
uv run python scripts/compare_requirement_support.py --inputs .tmp/impact-lexical-baseline.json,.tmp/impact-lexical-ablation.json,.tmp/impact-fitcv.json,.tmp/impact-current-hash.json --output .tmp/fitcv-impact-report.json
```

Dry-run paired live evaluation after offline acceptance:

```powershell
uv run python scripts/evaluate_requirement_support_live.py --input path/to/paired-evaluation.json --output .tmp/live-dry-run.json
```

Dry-run validates fixture, scenario, model, template, generation settings, and output-budget parity without provider calls. Do not report final generated-CV quality, provider token usage, or retrieval optimization gains from offline benchmark output alone.

Authorized live paired evaluation:

```powershell
$env:FITCV_LLM_API_KEY = '<load from local .env without printing it>'
uv run python scripts/evaluate_requirement_support_live.py --input path/to/paired-evaluation.json --output .tmp/live-result.json --live
```

Live inputs must include one prompt and deterministic review rubric per baseline/FitCV variant. The evaluator makes exactly two calls per pair, records sanitized response metadata and provider usage, and reports baseline, FitCV, and `fitcv_minus_baseline` metrics separately. It does not repair or persist generated CV text.

### RAG impact test-suite handoff — 2026-09-25

Prepare the source-backed, sanitized corpus before any generation run:

```powershell
uv run python scripts/prepare_rag_impact_corpus.py --input data/linkedin-2026-09-25-22-54-17.json --base-fixture tests/fixtures/rag_impact_benchmark.json --output .tmp/rag-impact-derived-corpus.json --seed 20260925
```

Run offline contract and metric proof:

```powershell
uv run pytest -q tests/test_prepare_rag_impact_corpus.py tests/test_rag_impact_dataset.py tests/test_evaluate_requirement_support_live.py tests/test_compare_rag_impact.py tests/test_rag_impact_review_protocol.py tests/test_rag_impact_review_agents.py
uv run python scripts/compare_rag_impact.py --help
```

Reviewer roles are `grounding-reviewer`, `recruiter-quality-reviewer`, and
`review-adjudicator`. They receive blinded paired outputs, emit versioned JSON
annotations, and never receive arm identity, raw CV text, or authority to alter
outputs. See `docs/rag-impact-review-protocol.md` and
`docs/rag-impact-review-agents.md`.

Run existing deterministic benchmark arms separately from full-profile versus
RAG generation impact. Use `scripts/compare_rag_impact.py` only when fixture,
rubric, model/template, generation settings, and scenario fingerprints match.
Failed calls, missing reviews, unresolved adjudication, and unavailable cost
remain visible in reports and cannot improve gate decisions.

Live execution requires explicit approval for provider/model, credential source,
maximum spend, reviewer coverage, held-out lock, and raw-output handling. Keep
the source and generated outputs outside Git; record hashes and sanitized
metrics only. No live quality claim follows from offline or mocked output.

Offline acceptance evidence from September 25, 2026: the focused suite passed
35 tests. Corpus preparation produced source SHA-256
`5f934050146069035b84ec186846de79056339892657dc2e615a4f84198f69c5`, exact
splits of 10 development, 10 pilot, and 20 held-out cases, and corpus SHA-256
`f293bba4979b35acf1f2215de0bd8f96c67a1d832d946eb2d0dd8725f37bec39`.
Lexical ablation and requirement-aware arms each ran 50 measured runs with 5
warmups, shared fixture SHA-256
`d0ce5b4e52addfc1be2a107dd7900892e84733a34cc341ad003bdf6f102f7d40`, and
`provider_calls: false`. Selected requirement recall was `0.933333` for
ablation and `1.0` for requirement-aware; selected evidence-pair recall was
`0.875` and `0.9375`. Existing validation cases passed `6/17` in both outputs;
that fixture limitation is retained as a report caveat, not converted into a
quality claim.

### Impact measurement result — 2026-09-25

- Offline run used 16 independent scenarios, 50 measured runs, 5 warmups, and fixture SHA-256 `c35c1d9027809e8cad204e048e1c7d89c304013b22e98e91bc9404e9e6923c3c`.
- FitCV selected requirement recall `1.0` and evidence-pair recall `0.9375`; conventional baseline and ablation reached `0.933333` and `0.875`. A/C and B/C deltas were `+0.066667` and `+0.0625`; C/D deltas were `0.0`.
- Explicit-link arms reported assignment precision `1.0`; conventional baseline precision is `not_applicable`. No incorrect pairs appeared.
- Offline gate passed. Authorized live run used 6 paired scenarios, 12 provider calls, model `cx/gpt-5.6-luna`, and fixture SHA-256 `c35c1d9027809e8cad204e048e1c7d89c304013b22e98e91bc9404e9e6923c3c`.
- Live result: baseline and FitCV both reached requirement coverage `1.0`, unsupported factual claim rate `0.0`, first-pass acceptance `1.0`, and final acceptance `1.0`; FitCV minus baseline was `0.0` for each metric. Provider usage reported `34,965` total tokens; cost was unavailable.
- Live review uses `deterministic_fixture_rubric_v1`, so results measure fixture-term coverage and marked unsupported claims, not human stylistic quality. Keep production retrieval and selection defaults unchanged; next optimization requires a live workload where offline selection differs.

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
