# Structured CV Representation Implementation Plan

> **For agentic workers:** Execute this plan task-by-task with verification after each task. Use checkbox tracking and keep markdown CV flows working throughout the rollout.

**Goal:** Introduce a structured intermediate CV representation that is persisted alongside markdown, while preserving current markdown downloads and run-detail behavior.

**Architecture:** Add a schema-versioned structured CV artifact to the generation pipeline, render markdown from that structured document, persist both artifacts in `cv_versions`, and expose structured data to downstream export readers without parsing markdown.

**Tech Stack:** Python, FastAPI, BigQuery, Jinja2

**Source spec:** `docs/superpowers/specs/2026-03-29-structured-cv-representation-design.md`

**Affected feature contract:** `docs/features/cv_system/cv_system.yaml`

**Supporting docs to update during implementation:**

- `docs/features/cv_system/cv_system.yaml`
- `docs/features/cv_system/history.md`
- `docs/features/trigger_run_management/history.md`

---

## Task 1: Define Structured CV Artifact Schema

**Files:**

- Modify: `src/fitcv/cv_generator.py`
- Modify: `tests/test_cv_generator.py`

- [ ] **Step 1.1: Add an explicit structured CV schema shape**
  - Define the canonical `cv_doc_v1` shape in `src/fitcv/cv_generator.py`
  - Keep first-rollout validation helpers in `cv_generator.py` rather than introducing a separate schema module
  - Include:
    - `schema_version`
    - `preset`
    - `job_url`
    - `fit_classification`
    - `target_role`
    - `sections.header`
    - `sections.summary`
    - `sections.experience`
    - `sections.projects`
    - `sections.education`
    - `sections.skills.groups`
    - `sections.certifications`
    - `sections.languages`

- [ ] **Step 1.2: Add schema validation helpers**
  - Validate required top-level keys
  - Enforce stable empty-shape behavior:
    - lists use `[]`
    - optional scalars may use `null`
    - supported schema sections are always present, even when empty
  - Avoid ad hoc markdown parsing

- [ ] **Step 1.3: Write failing unit tests for schema validation**
  - valid structured CV passes
  - missing required sections fail
  - malformed `skills.groups` fails
  - empty-list defaults are preserved

- [ ] **Step 1.4: Confirm tests pass**

---

## Task 2: Split Generation Into Structured Output and Rendering

**Files:**

- Modify: `src/fitcv/cv_generator.py`
- Modify: `tests/test_cv_generator.py`

- [ ] **Step 2.1: Introduce the preferred generation contract**
  - Add `generate_structured_cv(...) -> dict[str, Any]`
  - Add `render_cv_markdown(structured_cv, config) -> str`

- [ ] **Step 2.2: Keep rollout compatibility**
  - Preserve `generate_cv(...)` temporarily as a wrapper returning:
    - `{"structured_cv": ..., "markdown": "..."}`
  - Ensure existing callers do not break mid-rollout

- [ ] **Step 2.3: Align structured output to preset/composition/content-rules**
  - Structured CV output must reflect the active CV preset
  - Section presence/content must follow the current composition settings
  - Content rules still apply to the semantic document, not only to markdown text

- [ ] **Step 2.4: Write failing tests for structured-first generation**
  - verify markdown render consumes structured output
  - verify wrapper preserves backward-compatible behavior during rollout
  - verify model selection still comes from nested CV config

- [ ] **Step 2.5: Confirm tests pass**

---

## Task 3: Persist Structured CV and Generation Metadata

**Files:**

- Modify: `src/fitcv/tracker.py`
- Modify: `assets/bigquery/cv_versions.sql`
- Modify: `scripts/bootstrap_bigquery.py`
- Add: `scripts/migrations/<new_migration>.py`
- Modify: `tests/test_tracker.py`

- [ ] **Step 3.1: Extend `cv_versions` artifact model**
  - Add persisted fields:
    - `cv_structured_json`
    - `cv_schema_version`
    - `cv_generation_model`
    - `cv_prompt_version`
  - Optionally add:
    - `cv_render_variant`
    - `cv_render_locale`

- [ ] **Step 3.2: Update `create_cv_version_record()`**
  - Accept structured CV payload
  - Accept generation metadata
  - Serialize only validated structured CV payloads for BigQuery persistence
  - Derive `cv_schema_version` from the structured document itself, not from a disconnected constant

- [ ] **Step 3.3: Write failing tracker tests**
  - stored record contains structured JSON
  - stored record contains schema version
  - stored record contains generation metadata
  - historical fields remain intact

- [ ] **Step 3.4: Add BigQuery migration**
  - Extend `cv_versions` schema safely
  - Keep historical rows valid with nullable new fields
  - Keep the migration path and owning DDL/bootstrap declarations aligned

- [ ] **Step 3.5: Confirm tests pass**

---

## Task 4: Integrate Structured CV Into the Pipeline

**Files:**

- Modify: `src/fitcv/pipeline.py`
- Modify: `tests/test_pipeline.py`

- [ ] **Step 4.1: Replace markdown-only pipeline flow**
  - Generate structured CV first
  - Validate structured CV before persistence
  - Render markdown from the validated structured CV
  - Persist both artifacts through the tracker
  - Pass through generation metadata needed by persistence:
    - `cv_generation_model`
    - `cv_prompt_version`
    - `cv_schema_version`

- [ ] **Step 4.2: Preserve current run behavior**
  - existing `fit == "skip"` handling stays intact
  - existing validation/retry logic remains compatible
  - existing CV markdown downloads still work

- [ ] **Step 4.3: Add failing pipeline tests**
  - structured CV is validated before write
  - markdown comes from structured CV, not a parallel text path
  - stored version record includes structured payload and metadata

- [ ] **Step 4.4: Confirm tests pass**

---

## Task 5: Extend Run Results Export to Read Structured CV

**Files:**

- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv_cp/bq_store.py` if the run/export read model needs field mapping changes
- Modify: `src/fitcv_cp/app.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`
- Modify: `tests/test_fitcv_cp/test_bq_store.py` if read-model mapping changes
- Modify: `tests/test_fitcv_cp/test_app.py`

- [ ] **Step 5.1: Extend export `cv` payload**
  - Extend the existing run-results export snapshot rather than designing a new export surface
  - Keep ownership primarily in the pipeline/worker path because this codebase persists the export snapshot at run time, and the control plane serves that stored snapshot later
  - Include:
    - `model_used`
    - `prompt_version`
    - `schema_version`
    - `structured`
    - `markdown`
    - `created_at`

- [ ] **Step 5.2: Keep export backward-compatible**
  - For historical CV rows without structured data:
    - `structured = null`
    - `schema_version = null`
  - Markdown remains present when available

- [ ] **Step 5.3: Write failing export tests**
  - structured CV appears for new rows
  - historical rows remain valid
  - endpoint still downloads readable JSON

- [ ] **Step 5.4: Confirm tests pass**

---

## Task 6: Update Run Detail and CV Inspection Read Paths

**Files:**

- Modify: `src/fitcv_cp/bq_store.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Modify: `tests/test_fitcv_cp/test_bq_store.py`
- Modify: `tests/test_fitcv_cp/test_app.py`

- [ ] **Step 6.1: Extend CV read models**
  - Ensure control-plane reads can fetch structured CV fields from `cv_versions`
  - Keep existing markdown-only readers intact where possible

- [ ] **Step 6.2: Decide first UI exposure scope**
  - Minimum scope: no visual redesign, but data is available to export/readers
  - Do not add a new structured-CV inspection UI in this rollout unless it is trivially low-risk
  - Existing markdown inspection/download behavior must remain unchanged

- [ ] **Step 6.3: Add failing read-layer/app tests**
  - markdown downloads still work
  - structured fields are available in read paths for new rows

- [ ] **Step 6.4: Confirm tests pass**

---

## Task 7: Update Feature Docs

**Files:**

- Modify: `docs/features/cv_system/cv_system.yaml`
- Modify: `docs/features/cv_system/history.md`
- Modify: `docs/features/trigger_run_management/history.md`

- [ ] **Step 7.1: Update feature contract**
  - Add structured CV representation capability
  - Link spec and implementation plan

- [ ] **Step 7.2: Record implementation history**
  - note schema change
  - note dual-artifact persistence
  - note export/read-path implications

---

## Execution Order

1. Complete Task 1 and Task 2 first so the generator contract is stable.
2. Complete Task 3 before wiring pipeline persistence.
3. Complete Task 4 before extending export/read paths.
4. Complete Task 5 and Task 6 after structured CV data is flowing end-to-end.
5. Complete Task 7 last so feature docs match the implemented behavior.

---

## Verification Checklist

- [ ] Structured CV output is validated against an explicit schema before persistence
- [ ] Markdown rendering consumes the structured CV document rather than a parallel free-text path
- [ ] `cv_versions` persists both markdown and structured CV data for new rows
- [ ] Historical rows without structured CV remain supported
- [ ] Run results export can include structured CV and generation metadata without parsing markdown
- [ ] Existing markdown download flows remain intact

---

## Risks and Notes

### Generator Rollout Risk

The riskiest seam is changing the CV generation contract without breaking existing pipeline callers. Use a compatibility wrapper while introducing `generate_structured_cv(...)` and `render_cv_markdown(...)`.

### Schema Drift Risk

The structured CV artifact must be schema-versioned from the first rollout. Do not introduce unversioned nested JSON blobs.

### Composition Alignment Risk

The structured CV document should reflect the active preset/composition/content-rules contract for the run. Avoid letting the generator emit arbitrary sections that the composition system would later suppress.

### Scope Guard

Do not broaden this implementation into a full CV editor. The first objective is durable semantic storage plus compatibility with current markdown flows.
