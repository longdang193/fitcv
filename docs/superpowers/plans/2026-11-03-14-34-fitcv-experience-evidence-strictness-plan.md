---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
contract_version: "1"
name: fitcv-experience-evidence-strictness
targets:
  - config/policy/cv_analysis.yaml
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/app.py
  - src/fitcv/evidence.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/pipeline.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/sqlite_store.py
  - frontend/src/features/pipeline-settings/types.ts
  - frontend/src/features/pipeline-settings/sections-def.ts
  - frontend/src/features/pipeline-settings/pipeline-settings-dialog.tsx
  - frontend/src/features/runs/types.ts
  - frontend/src/features/job-evaluation/components/PipelineOutcome.tsx
  - frontend/src/features/run-detail/run-detail-page.tsx
  - docs/pipeline.md
  - docs/configuration.md
  - tests/test_fitcv_cp/test_settings_schema.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - tests/test_agentic_cv_analysis.py
  - tests/test_evidence.py
  - frontend/src/test/pipeline-settings.test.tsx
  - frontend/src/test/job-evaluation.test.ts
  - frontend/src/test/runs.test.ts
---

# FitCV Experience Evidence Strictness

## Review Findings

The two submitted model reviews examined the same immutable revision,
`e70489f7313ad1397f19128a288b40220be453bb`, in read-only mode. GPT-5.6-Sol
completed normally. GPT-6 produced a persisted response, but the runner's final
Markdown locator timed out while settling completion; that is a review-runner
extraction defect, not evidence of a FitCV product defect. The GPT-6 response was
still manually validated against the pinned source before including findings.

Only findings confirmed by both model output and local source inspection are
carried into this plan:

1. **High — Pipeline ownership is projection-driven.** `SETTINGS_SCHEMA` is not
   sufficient: `src/fitcv_cp/app.py:8285-8310` derives `pipeline_owned_keys`
   from `pipeline_settings_projection()`, and `src/fitcv_cp/app.py:8353-8369`
   rejects unsupported PATCH keys. The CV Analysis projection currently lives at
   `src/fitcv_cp/settings_schema.py:2035-2051`. Attribution: GPT-5.6-Sol and
   GPT-6; confidence high.
2. **High — The settings UI has no enum control.** The field union at
   `frontend/src/features/pipeline-settings/types.ts:12-23` and renderer at
   `frontend/src/features/pipeline-settings/pipeline-settings-dialog.tsx:538-617`
   support membership, boolean, number, and read-only fields, not a validated
   three-state value. Attribution: GPT-5.6-Sol and GPT-6; confidence high.
3. **High — CV-analysis reuse identity omits the new policy.**
   `src/fitcv/evidence.py:716-731` builds the contract fingerprint without an
   experience-evidence mode, while `src/fitcv/agentic_cv_analysis.py:1049-1078`
   uses it to reuse analysis records. A Strict run could therefore reuse a Full
   or Loose result. Attribution: GPT-5.6-Sol and GPT-6; confidence high.
4. **High — The current analyzer exits before evidence review for reranker
   `skip`.** `src/fitcv/agentic_cv_analysis.py:998-1047` returns
   `reranker_blocked_before_analysis` before building evidence. Loose cannot
   surface a defensible borderline recommendation if the feature is implemented
   only in the final prompt. Attribution: GPT-5.6-Sol and GPT-6; confidence high.
5. **Medium — Strict replay policy identity omits CV-analysis policy.**
   `src/fitcv_cp/app.py:820-831` signs ranking, CV, pipeline, and prompt fields,
   while `src/fitcv_cp/app.py:14650-14659` compares that signature during strict
   continuation. The missing CV-analysis policy version is confirmed; the
   operational impact is medium because it depends on replay mode and the
   continuation path. Attribution: GPT-6; confidence high for the gap and
   medium for impact.
6. **Medium — Legacy defaults and existing tests do not cover this enum across
   layers.** Runtime defaults are resolved at
   `src/fitcv_cp/settings_schema.py:636-663`, old run snapshots load through
   `src/fitcv_cp/app.py:2911-2925`, and current settings tests mostly cover
   numeric/boolean behavior. The feature needs explicit Full compatibility,
   API, runtime, cache, replay, behavioral, and UI regression coverage.
   Attribution: GPT-5.6-Sol and GPT-6; confidence high.

The review did **not** validate a need for a new service, database table, new
settings endpoint, universal project-score multiplier, or automatic student/senior
defaulting. Those are excluded below.

## Current Review Corrections

The GPT-5.6-Sol High review of immutable commit
`ffcb2e92d925ae88992cca42557fa3029b9a96b4` supersedes the earlier review list
above for implementation execution. Each correction was checked against the
pinned plan and source at that commit.

1. **High — Loose routing has a second skip gate.** Task 3 bypasses only the
   early `ranking_fit_label == "skip"` path, but
   `src/fitcv/agentic_cv_analysis.py:1157-1171` still returns the skipped status
   after evidence retrieval, and `src/fitcv/pipeline.py:1748-1755` discards the
   gap fit. Add an explicit Loose-only downstream transition to
   `fit_classification="stretch"` for an experience-only gap and test the final
   status/classification. Confidence: 99%.
2. **High — Responsibility evidence is outside the source policy.** Task 3 names
   `_assess_requirement_support()`, but production/ownership/leadership claims
   use `_assess_responsibility_support()` through
   `_responsibility_support_map()` and `_annotate_responsibility_support()` at
   `src/fitcv/evidence.py:2403-2465`, `:2657-2689`, and `:3207-3211`.
   Include this path in the mode-aware policy or unify both paths behind one
   helper, with project/employment fixtures for all modes. Confidence: 99%.
3. **High — CV-evaluation persistence is not the run-job projection source.**
   Task 4 writes `cv_evaluations.evidence_json`, while `/runs/{run_id}/jobs`
   hydrates `run_job_stage_results.evidence_json` through
   `src/fitcv_cp/sqlite_store.py:13788-13840`. Add the projection bridge and a
   store/API test asserting the actual response. Confidence: 99%.
4. **Medium — Replay signatures need legacy compatibility.** Adding mode/version
   fields to the unversioned `_policy_envelope_signature()` can make old manual
   checkpoints fail strict replay even when omitted mode resolves to Full.
   Version the replay envelope or validate legacy signatures before emitting the
   new signature, and add a prior-signature checkpoint regression. Confidence:
   97%.
5. **Medium — The new key can receive `cv_generation` metadata.** The schema
   metadata special case only covers `cv_analysis.semantic_alignment.*`; the
   generic `cv_` fallback assigns `cv_generation`. Task 1 must explicitly assign
   `stage=cv_analysis` and `control_surface=agentic_runtime`, with a metadata
   regression. Confidence: 98%.

All five findings are independently confirmed by separate source paths; no
second-model corroboration was requested for this execution.

## Goal

Add a per-run and saved Pipeline Settings control named **Match strictness**
with **Loose**, **Full**, and **Strict** values, defaulting to **Full**. The
setting controls how transferable project evidence is used when FitCV evaluates
experience-shaped job requirements, while keeping capability evidence,
professional-tenure evidence, recommendation labels, and CV-generation claims
separate and traceable.

## Implementation Outcomes

### 1. Validated, backward-compatible setting

`cv_analysis.experience_evidence_mode` is a canonical string enum with values
`loose`, `full`, and `strict`, default `full`. It is available through the
existing Pipeline Settings GET/PATCH/reset APIs, supports run-level overrides,
and appears in the existing CV Analysis settings projection. Omitted values in
legacy configuration and old run snapshots resolve to `full` without rewriting
historical records.

### 2. Source-aware evaluation policy

The evaluator preserves current Full behavior and distinguishes:

- a project demonstrating a technical capability;
- employment-backed professional tenure or workplace responsibility;
- senior-level scope, ownership, duration, and production context; and
- explicit job-description acceptance of academic/project evidence.

Loose may surface a plausible borderline job as a stretch when a project
demonstrates the core capability, but it records the missing professional
qualifier. Strict requires employment-backed evidence for explicit professional
tenure, years, seniority, leadership, ownership, or production-responsibility
requirements unless the job description explicitly accepts academic/project
evidence. No mode invents employment, tenure, or production ownership.

### 3. Stable run, cache, and replay semantics

The resolved mode and policy version are frozen in `effective_settings_json`,
included in CV-analysis reuse identity, and included in strict replay policy
identity. Changing saved settings after a run does not change that run. Changing
mode cannot reuse a result produced under another mode; same-mode reuse remains
valid.

### 4. Separate recommendation and evidence verdicts

The existing recommendation signal (`ranking_fit_label` / `fit_classification`)
remains distinct from a new structured experience-evidence summary derived from
`requirement_coverage`. The run-job API and job evaluation UI expose both, for
example: `Worth exploring` plus `Built a sales dashboard in Power BI` and
`Commercial deployment unverified`. CV generation continues to consume only
verified evidence claims.

### 5. Regression and documentation coverage

Backend, persistence, cache, replay, frontend interaction, and representative
behavior tests prove Full parity and the Loose/Strict differences. Pipeline and
configuration documentation explains when to choose each mode and explicitly
states that student status alone does not select a default.

## Scope Decisions And Non-Goals

- Use the backend key `cv_analysis.experience_evidence_mode`; use the UI label
  `Match strictness` and the option labels `Loose`, `Full`, and `Strict`.
- Keep `Full` as the default and preserve current behavior under `Full`.
- Do not infer the default from student/senior status. The first implementation
  gives the user the control and documents role-based guidance; it does not add
  a hidden heuristic that silently changes the selected mode.
- Do not alter AI ranking scores, embedding similarity, global fit thresholds,
  hard location/language/contract filters, or CV-generation prompt authority.
- Do not make project evidence impersonate `experience_entry` evidence.
- Do not rewrite historical settings snapshots, old analysis records, or old
  database rows. Use compatibility defaults when reading them.
- Do not add a database migration: the existing JSON settings/evaluation
  payloads and run-job projection are sufficient.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `none`
- Default task executor: `codex`
- Required skills: `skill-backend-verification`, `skill-full-stack-integration`,
  `skill-code-standards`, `skill-test-driven-development`, and
  `skill-verification-before-completion`
- Isolation: `current workspace`; preserve all unrelated untracked files
- Commit policy: `no commits during execution`; commit/push is a separate
  explicitly authorized disposition
- Preauthorized local actions: edit only the listed implementation, test, and
  documentation paths; run the listed focused tests, frontend typecheck/build,
  and repository verification commands
- User-approval actions: push, merge, publish, delete unrelated files, rewrite
  historical records, or broaden the setting into ranking-policy changes
- Parallel ownership: none; `settings_schema.py`, `app.py`, `evidence.py`, and
  the shared evaluation contract are serialized owners
- Sequential fallback: execute Tasks 1–6 in order and do not start a consumer
  task until its canonical contract assertions pass

## Task Breakdown

### Task 1: Register the Match strictness contract

**Purpose:** Make the setting a single, validated source of truth across the
canonical policy file, Python schema, and Pipeline Settings projection.

**Task Function:** backend configuration contract

**Template Profile:** unresolved at activation; select the lowest discovered
profile that reliably handles typed configuration and compatibility behavior

**Specification Coverage:** Outcomes 1 and 5; findings 1 and 6.

**Required Skills:** `skill-code-standards`, `skill-test-driven-development`.

**Files And Symbols:**

- `config/policy/cv_analysis.yaml`: `cv_analysis` defaults.
- `src/fitcv_cp/settings_schema.py`: `SETTINGS_SCHEMA`,
  `settings_schema_with_runtime_defaults()`, and
  `pipeline_settings_projection()`.
- `tests/test_fitcv_cp/test_settings_schema.py`: schema, validation, default,
  config-path, and projection tests.

**Dependencies:** none.

**Authority:**

- Preauthorized local actions: edit the three listed files and run the focused
  schema tests.
- Stop for: any need to rename existing settings, change unrelated defaults,
  add a new persistence mechanism, or alter ranking policy.

**Steps:**

1. Add `experience_evidence_mode: full` below `cv_analysis` in the canonical
   policy YAML.
2. Add one `SETTINGS_SCHEMA` entry with key
   `cv_analysis.experience_evidence_mode`, type `str`, declared default `full`,
   options `loose`, `full`, `strict`, UI label `Match strictness`, a description
   explaining capability versus professional-experience evidence, the nested
    config path `cv_analysis.experience_evidence_mode`, and explicit
    `stage=cv_analysis` plus `control_surface=agentic_runtime` metadata. Do not
    rely on the generic `cv_` stage fallback.
3. Add a direct editable row to the CV Analysis `Evidence Scope` projection so
   the backend GET includes the field and the existing PATCH ownership set
   accepts it.
4. Preserve `full` when the baseline config omits the path. Ensure blank and
   unknown values fail through the existing validation path rather than being
   silently coerced.
5. Extend schema tests to assert the enum metadata, options, default,
   `apply_settings_to_config()` nested output, invalid-value rejection, and
   projection ownership.

**Verification:**

```powershell
uv run pytest tests/test_fitcv_cp/test_settings_schema.py -q
```

The focused suite must prove all three values are accepted, invalid and blank
values are rejected, omitted configuration resolves to `full`, and the
projection owns the key.

**Exit Criteria:** The canonical policy, schema registry, and backend projection
agree on one key, one path, three values, and one default; no API/UI task can
observe an unregistered setting.

### Task 2: Freeze mode in runs, analysis reuse, and replay

**Purpose:** Prevent mode drift and stale cross-mode reuse.

**Task Function:** runtime configuration and reproducibility

**Template Profile:** unresolved at activation; select the lowest discovered
profile that reliably handles persistence, fingerprints, and replay contracts

**Specification Coverage:** Outcome 3; findings 3, 5, and 6.

**Required Skills:** `skill-backend-verification`, `skill-test-driven-development`.

**Files And Symbols:**

- `src/fitcv_cp/app.py`: run effective-config construction around
  `_execute_trigger`, `_policy_envelope_signature()`, and
  `_load_run_effective_config_snapshot()`.
- `src/fitcv/evidence.py`: `build_cv_analysis_contract_fingerprint()` and
  `build_cv_analysis_input_fingerprint()`.
- `src/fitcv/agentic_cv_analysis.py`: `_build_analysis_input_components()`,
  reuse comparison, and `analyze_ranked_job()`.
- `src/fitcv_cp/worker_job.py`: regeneration input/settings snapshot path.
- `tests/test_fitcv_cp/test_app.py`, `tests/test_fitcv_cp/test_worker_job.py`,
  and `tests/test_agentic_cv_analysis.py`.

**Dependencies:** Task 1.

**Authority:**

- Preauthorized local actions: edit the listed runtime and test symbols; add
  deterministic fingerprint and replay assertions.
- Stop for: any requirement to rewrite historical snapshots, invalidate all
  unrelated reuse contracts, or change replay behavior outside CV-analysis
  policy identity.

**Steps:**

1. Verify that saved settings and per-run `config_overrides` resolve the mode
   before `effective_settings_json` is serialized. Preserve the resolved value
   in the existing nested config; do not add a second run-setting store.
2. Define one `EXPERIENCE_EVIDENCE_POLICY_VERSION` constant in
   `src/fitcv/evidence.py` and use that same imported value in the analysis
   fingerprint and replay envelope. Add the resolved mode to
   `build_cv_analysis_contract_fingerprint()`. Keep job-specific seniority and
   requirement text in the existing input payload so changing them changes the
   input fingerprint without duplicating them in the global contract.
3. Add the CV-analysis policy version and resolved mode to
   `_policy_envelope_signature()` so strict continuation detects policy drift.
4. Make `_load_run_effective_config_snapshot()` resolve a missing
   `cv_analysis.experience_evidence_mode` to `full` only in memory when reading
   an old run; do not mutate the stored JSON.
5. Verify worker regeneration reads the run-effective snapshot and cannot pick
   up a newly changed saved setting after the run was created.
6. Add legacy-signature compatibility before emitting the new replay signature:
   validate old checkpoint signatures against the old envelope shape, resolve
   omitted mode to Full, and use the new signature only for subsequent
   checkpoints. Add a prior-signature checkpoint regression.
7. Add tests for explicit Full versus omitted Full identity, cross-mode cache
   misses, same-mode cache hits, seniority/input fingerprint changes, old
   snapshots, strict replay drift, and run-level override persistence.

**Verification:**

```powershell
uv run pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py tests/test_agentic_cv_analysis.py -q
```

The tests must show that a saved-settings change after run creation does not
alter the run, a mode change cannot reuse a prior analysis, same-mode reuse is
still accepted, and old snapshots continue as Full.

**Exit Criteria:** Every analysis and replay decision has an attributable mode
and policy identity, with no historical-record rewrite.

### Task 3: Implement source-aware experience evidence policy

**Purpose:** Apply Loose/Full/Strict to requirement qualification without
changing the meaning of verified claims.

**Task Function:** evidence-policy implementation

**Template Profile:** unresolved at activation; select the lowest discovered
profile that reliably handles evidence provenance and behavioral regression work

**Specification Coverage:** Outcomes 2 and 4; findings 4 and the evidence
provenance constraints.

**Required Skills:** `skill-backend-verification`, `skill-test-driven-development`.

**Files And Symbols:**

- `src/fitcv/evidence.py`: requirement qualifier parsing,
  `_normalise_experience_entry()`, `_normalise_project_entry()`,
  `_assess_requirement_support()`, `_assess_responsibility_support()`,
  `_responsibility_support_map()`, `_annotate_responsibility_support()`,
  `build_cv_analysis_contract_fingerprint()`, and the requirement-support
  policy version.
- `src/fitcv/agentic_cv_analysis.py`: `_build_requirement_coverage()`,
  `build_cv_analysis_record()`, and `analyze_ranked_job()`.
- `src/fitcv/pipeline.py`: CV-analysis result projection and decision-chain
  preservation if the new summary must be carried into persisted job output.
- `tests/test_evidence.py` and `tests/test_agentic_cv_analysis.py`.

**Dependencies:** Tasks 1 and 2.

**Authority:**

- Preauthorized local actions: add the mode-aware policy and tests in the
  listed evidence/analyzer owners; preserve existing output keys unless the
  new summary is additive.
- Stop for: any proposal to multiply project scores globally, label a project
  as employment, relax hard eligibility filters, or make CV generation consume
  unverified evidence.

**Steps:**

1. Add one resolver that reads `cv_analysis.experience_evidence_mode` and
   defaults missing values to `full`.
2. Extend the existing requirement descriptor/parser only enough to identify
   explicit academic/project acceptance and experience-shaped qualifiers such
   as duration, commercial/professional context, production responsibility,
   ownership, leadership, or seniority. Keep the existing requirement IDs and
   qualifier evidence trace intact.
3. Preserve the Full branch as the current `_assess_requirement_support()`
   behavior.
4. Implement Loose so a project can support a capability-shaped requirement or
   a borderline experience-shaped requirement when the concrete task is shown,
   while emitting a professional-experience gap whenever employment tenure,
   commercial context, production ownership, or a required duration is absent.
5. Implement Strict so project evidence remains valid technical evidence but
   cannot satisfy employment-backed tenure, years, seniority, leadership,
   ownership, or production-responsibility claims unless the JD explicitly
   accepts academic/project evidence. Preferred requirements remain
   non-blocking under the existing semantics.
 6. Apply the same source-aware policy to the responsibility-support path. Do
    not allow `_assess_responsibility_support()` to treat `project_entry` as
    employment-backed evidence for production, ownership, leadership, tenure,
    or duration claims unless the JD explicitly accepts project evidence.
 7. Add an additive experience-evidence summary to the analysis record with the
   mode, capability status, professional status, gap reasons, and source
   evidence IDs. Keep `requirement_coverage` authoritative for verified claims
   and keep `do_not_claim` populated for unsupported professional qualifiers.
 8. Add a named helper
   `should_route_loose_experience_review(job, profile, config)` beside the
   analyzer's ranking-fit helpers. It returns true only when the resolved mode
   is Loose, the ranking result is a valid `skip` (not ranking-unavailable), the
   candidate evidence projection contains a canonical capability match for at
   least one required requirement, and the remaining gap is limited to an
   experience qualifier rather than a hard eligibility factor. Use that helper
   in the `ranking_fit_label == "skip"` early path. Full and Strict retain the
   current early skip behavior; unavailable ranking data and hard eligibility
   failures remain immediately blocked.
 9. After evidence review, apply a Loose-only downstream transition: when the
    ranking skip is valid and the remaining gap is experience-only, preserve
    `ranking_fit_label="skip"` as the recommendation input but emit
    `fit_classification="stretch"` and the normal completed analysis record.
    Full and Strict retain the existing skip behavior for unresolved blocking
    gaps.
 10. Keep `ranking_fit_label` as the recommendation input and
   `fit_classification` as the downstream fit result; do not overwrite either
   with the evidence-gap status.

**Verification:** Add deterministic fixtures covering:

- project-only evidence for “build a Power BI dashboard” — capability support
  is visible in all modes;
- “commercial experience preferred” — remains eligible in Strict because it is
  preferred, not a blocking must-have;
- “two years of production dashboard ownership required” — Loose may surface a
  stretch with an explicit gap, Full preserves baseline behavior, and Strict
  reports a must-have gap without claiming the two years;
- a JD explicitly accepting academic projects — project evidence can satisfy
  the stated requirement in Strict; and
- employment-backed evidence — qualifies the professional requirement in all
  modes when the existing qualifier checks support it.
- a responsibility entity backed only by `project_entry` evidence versus the
  same responsibility backed by employment evidence — Strict preserves the
  professional gap for the project and accepts the employment evidence;
- the Loose downstream transition — a valid experience-only reranker skip ends
  as a stretch analysis result rather than `SKIPPED_FIT_GATE_STATUS`.

Run:

```powershell
uv run pytest tests/test_evidence.py tests/test_agentic_cv_analysis.py -q
```

**Exit Criteria:** The mode changes only evidence qualification and borderline
review routing, keeps provenance visible, preserves Full parity, and cannot
create an unverified employment or tenure claim.

### Task 4: Persist and expose recommendation plus evidence verdict

**Purpose:** Make the two different decisions available to API consumers and
the existing run/job surfaces without a database migration.

**Task Function:** backend contract integration

**Template Profile:** unresolved at activation; select the lowest discovered
profile that reliably handles existing API/resource contracts and persistence

**Specification Coverage:** Outcome 4.

**Required Skills:** `skill-full-stack-integration`, `skill-backend-verification`.

**Files And Symbols:**

- `src/fitcv/agentic_cv_analysis.py`: analysis record serialization.
- `src/fitcv_cp/worker_job.py`: `update_cv_evaluation()` evidence payload.
- `src/fitcv_cp/sqlite_store.py`: run-job projection hydration and pipeline
  snapshot evidence bridge.
- `src/fitcv_cp/app.py`: run-job resource assembly around the visible-row
  projection and CV-version/evaluation lookup.
- `src/fitcv/pipeline.py`: decision-chain and run-job output preservation.
- `tests/test_fitcv_cp/test_worker_job.py`, `tests/test_fitcv_cp/test_sqlite_store.py`,
  `tests/test_fitcv_cp/test_app.py`, and `frontend/src/test/runs.test.ts`.

**Dependencies:** Task 3.

**Authority:**

- Preauthorized local actions: extend existing JSON/resource projections and
  contract tests; do not add tables or endpoints.
- Stop for: any response-shape break for existing consumers, any need to
  change the authoritative `requirement_coverage` contract, or any request to
  store derived summaries outside the existing evaluation payload.

**Steps:**

1. Store the additive experience-evidence summary in the existing CV
   evaluation evidence JSON alongside `requirement_coverage` and
   `evidence_selection_summary`.
2. Carry the same additive summary into the existing
   `run_job_stage_results.evidence_json` projection, or make the existing
   hydrator explicitly join the persisted CV evaluation evidence. Do not add a
   new table or endpoint.
3. Preserve both recommendation fields (`ranking_fit_label`,
   `fit_classification`) and the new evidence summary when pipeline records are
   persisted and projected into run-job resources.
4. Add API assertions that the run-job payload contains the recommendation and
   mode-aware evidence gap while existing outcome/status fields remain stable.
5. Preserve absent summaries for historical jobs as `null`/empty compatibility
   values; do not synthesize a false verdict for old records.

**Verification:**

```powershell
uv run pytest tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_app.py -q
```

Assert that a Loose borderline job returns a recommendation plus an explicit
professional-evidence gap through the actual run-job resource, while
Full/Strict and historical records retain their existing response shape and
meaning.

**Exit Criteria:** Backend consumers can render recommendation and evidence
verdict independently, with no new persistence layer and no overclaiming.

### Task 5: Add accessible settings and job-result UI controls

**Purpose:** Let users select the mode and see the distinction between a job
recommendation and the evidence gap.

**Task Function:** frontend contract and interaction

**Template Profile:** unresolved at activation; select the lowest discovered
profile that reliably handles typed React controls and accessibility regression
proof

**Specification Coverage:** Outcomes 1 and 4.

**Required Skills:** `skill-full-stack-integration`, `skill-code-standards`.

**Files And Symbols:**

- `frontend/src/features/pipeline-settings/types.ts`: `PipelineFieldDef` union.
- `frontend/src/features/pipeline-settings/sections-def.ts`: CV Analysis
  `ownedKeys`, field definition, and fallback defaults.
- `frontend/src/features/pipeline-settings/pipeline-settings-dialog.tsx`:
  generic field renderer, dirty tracking, save, and restore behavior.
- `frontend/src/features/runs/types.ts`: `RunJobItem` evidence summary typing.
- `frontend/src/features/job-evaluation/components/PipelineOutcome.tsx`: dual
  recommendation/evidence display.
- `frontend/src/features/run-detail/run-detail-page.tsx`: job-row wiring.
- `frontend/src/test/pipeline-settings.test.tsx`,
  `frontend/src/test/job-evaluation.test.ts`, and
  `frontend/src/test/runs.test.ts`.

**Dependencies:** Tasks 1 and 4.

**Authority:**

- Preauthorized local actions: add one generic accessible select field and the
  additive job-result summary rendering; preserve existing styling and native
  dialog behavior.
- Stop for: any request to add three booleans, bypass backend validation, or
  make student/senior status silently change the selected value.

**Steps:**

1. Extend `PipelineFieldDef` with a validated select field carrying explicit
   option values and labels.
2. Add `cv_analysis.experience_evidence_mode` to the CV Analysis `ownedKeys`,
   field metadata, and fallback defaults with `full` as the fallback.
3. Render a native labelled `<select>` in the existing generic dialog. Reuse
   current dirty tracking, PATCH, section restore, global restore, offline
   fallback, and revision-conflict handling.
4. Type the additive run-job evidence summary and render recommendation and
   evidence status separately in the existing outcome/job-row surface. Use
   wording that distinguishes “Worth exploring” from “professional evidence
   unverified”; do not label a project as employment.
5. Add UI tests for option rendering, dirty/save/reset behavior, a11y label
   association, API response mapping, and the dual recommendation/evidence
   display.

**Verification:**

```powershell
Push-Location frontend
npm test -- --run src/test/pipeline-settings.test.tsx src/test/job-evaluation.test.ts src/test/runs.test.ts
npm run typecheck
npm run build
Pop-Location
```

**Exit Criteria:** The control is editable, keyboard-accessible, correctly
defaulted, and the job result communicates both recommendation and evidence
limits without changing backend authority.

### Task 6: Align documentation and run the full acceptance matrix

**Purpose:** Make the policy understandable and prove cross-layer behavior
before implementation handoff.

**Task Function:** documentation and final verification

**Template Profile:** unresolved at activation; select the lowest discovered
profile that reliably performs cross-layer verification and reconciliation

**Specification Coverage:** Outcome 5 and every acceptance criterion.

**Required Skills:** `skill-verification-before-completion` and
`skill-plan-document-reviewer`.

**Files And Symbols:**

- `docs/pipeline.md`: stage ownership, requirement coverage, and evidence
  authority.
- `docs/configuration.md`: Match strictness setting, defaults, and guidance.
- All tests added or updated by Tasks 1–5.

**Dependencies:** Tasks 1–5.

**Authority:**

- Preauthorized local actions: update the two documentation files and run the
  complete focused acceptance commands; reconcile only files named in this
  plan.
- Stop for: any failing unrelated baseline test, any unreviewed response-shape
  change, or any acceptance result that cannot distinguish capability support
  from professional-experience support.

**Steps:**

1. Document Loose, Full, and Strict with the dashboard examples, explicit gaps,
   Full default, and the rule that student status alone does not select a mode.
2. Document that recommendation labels and evidence verdicts are separate and
   that CV generation uses verified claims only.
3. Run the backend and frontend focused suites from Tasks 1–5.
4. Run the repository's broader unit suites for the touched backend and frontend
   surfaces, then inspect the diff for unrelated changes.
5. Reconcile every acceptance criterion below with fresh command output and
   record the completed implementation and verification cycle.

**Verification:**

```powershell
python -m pytest tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_agentic_cv_analysis.py tests/test_evidence.py -q
Push-Location frontend
npm test -- --run src/test/pipeline-settings.test.tsx src/test/job-evaluation.test.ts src/test/runs.test.ts
npm run typecheck
npm run build
Pop-Location
git diff --check
git status --short
```

**Exit Criteria:** Documentation, backend contracts, runtime identity,
behavioral fixtures, API projections, and UI behavior agree; Full parity and
Loose/Strict gap semantics are proven; unrelated working-tree files remain
untouched.

## Verification

The final implementation verification must prove all of the following:

- Schema validation accepts exactly `loose`, `full`, and `strict`; rejects blank
  and unknown values; and resolves omissions to `full`.
- GET, PATCH, expected-revision conflict, section reset, and global reset all
  operate on the new key through the existing settings API.
- A run-level override is captured in `effective_settings_json`; later saved
  setting changes do not affect that run; old snapshots continue as Full.
- Full reproduces current behavior for project-only, employment-only, and mixed
  profiles.
- Loose can surface a concrete project capability as a stretch while showing a
  missing professional qualifier.
- Strict does not accept project-only evidence for explicit professional
  tenure, years, seniority, ownership, leadership, or production requirements,
  except when the JD explicitly accepts academic/project evidence.
- Preferred requirements remain non-blocking, and hard eligibility filters are
  unchanged.
- No output claims professional employment, duration, or ownership from a
  project alone.
- Mode changes alter CV-analysis cache identity; same-mode reuse remains valid;
  relevant job/seniority changes alter input identity.
- Strict replay detects CV-analysis policy drift and preserves the recorded mode
  for compatible continuation.
- The UI select is accessible and integrated with existing save/reset/error
  flows, and job results show recommendation plus evidence verdict separately.

## Completion Criteria

- All six task exit gates pass with fresh output.
- The focused backend and frontend commands pass without modifying unrelated
  files.
- `git diff --check` is clean.
- Documentation matches the implemented contract and examples.
- A final verification record identifies the exact mode, policy version, cache,
  replay, API, and UI assertions that passed.
- The implementation was explicitly authorized and the plan is now `completed`
  after the post-implementation verification below.

## Final Verification Record

- Backend acceptance: `python -m pytest tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_agentic_cv_analysis.py tests/test_evidence.py -q` — `1154 passed, 1 skipped`.
- Frontend tests: `npm test -- --run src/test/pipeline-settings.test.tsx src/test/job-evaluation.test.ts src/test/runs.test.ts` — `3 files passed, 66 tests passed`.
- Frontend type safety: `npm run typecheck` — passed.
- Frontend production build: `npm run build` — passed; Vite emitted only the existing chunk-size warning.
- Repository hygiene: `git diff --check` — passed after restoring the repository's LF line endings; unrelated untracked files were preserved.
- Contract coverage: `loose`, `full`, and `strict` validation/defaulting, settings API projection/reset/conflict paths, run snapshot persistence, Full parity, Loose stretch semantics, Strict professional-evidence gaps, cache/replay policy identity, evidence persistence, and accessible UI rendering are covered by the updated tests and documentation.
