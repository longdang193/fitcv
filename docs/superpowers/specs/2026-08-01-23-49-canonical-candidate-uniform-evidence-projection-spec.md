---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: canonical-candidate-creation-uniform-evidence-projection
targets:
  - data/candidate_profile.v2.sample.yaml
  - data/candidate_profile.template.yaml
  - config/runtime/control_plane.yaml
  - src/fitcv/candidate.py
  - src/fitcv/evidence.py
  - src/fitcv/llm_runtime.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/models.py
  - src/fitcv_cp/reconciler.py
  - src/fitcv_cp/sqlite_store.py
  - tests/test_candidate.py
  - tests/test_candidate_profile_template_contract.py
  - tests/test_llm_runtime.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - tests/test_fitcv_cp/test_reconciler.py
  - docs/configuration.md
  - docs/fitcv-settings-ui-prototype.integration.md
  - docs/fitcv-settings-ui-prototype.html
  - docs/pipeline.md
  - src/fitcv_cp/templates/candidate_profile_detail.html
  - src/fitcv_cp/templates/candidate_profiles.html
related_features:
  - cv_system
related_stages:
  - cv-analysis
  - cv-generation
---

# Canonical Candidate Profile Creation and Uniform Evidence Projection

## Goal and Problem

### Problem

- current behavior or opportunity: Candidate Profile input is a hand-authored YAML contract. Non-technical users cannot upload an ordinary CV, review extraction and inference separately, or confirm corrections before a profile becomes pipeline-selectable. Its evidence collector also projects work experience, projects, and achievements through separate paths, while education is accepted by profile reference validation but excluded from evidence retrieval and scoring.
- affected users, systems, or maintainers: non-technical candidates uploading CVs, fresh graduates whose strongest evidence is academic, Candidate Profile ingestion, CV analysis, CV generation, and maintainers changing evidence-bearing profile sections.
- evidence:
  - `src/fitcv/candidate.py` requires the v1 `experiences`, `skills`, `projects`, `achievements`, and `preferences` sections and validates references against parent record IDs.
  - `src/fitcv/evidence.py` collects only experience, project, and achievement entries and assigns section-specific types, weights, quotas, and trimming behavior.
  - `tests/test_candidate.py` proves education IDs may satisfy `skills[].evidence_refs`, but no corresponding education item enters runtime evidence retrieval.
  - `src/fitcv_cp/sqlite_store.py` accepts only UTF-8 `.yaml` Candidate Profile uploads and passes them directly to the v1 loader.
- consequence of no change: users must understand internal YAML, ambiguous extraction and inference cannot be reviewed at their proper boundaries, semantically equivalent evidence receives different treatment by source section, and derived claims cannot always be traced to exact approved facts and original source material.

### Goal

- desired outcome: Markdown, DOCX, and YAML uploads move through one deterministic extraction/import, baseline review, controlled derivation review, and explicit confirmation lifecycle before producing one validated `CanonicalCandidateProfile`; every evidence-bearing statement projects through one deterministic `CandidateEvidenceItem` contract.
- observable success:
  - equivalent statements from experience, education, projects, achievements, certifications, or volunteering enter the same relevance and selection path
  - fresh graduates require no pipeline special case
  - Markdown, DOCX, and YAML creation inputs become indistinguishable after canonicalization
  - YAML may supply canonical values and IDs, but it cannot bypass baseline review, derived review, or final confirmation
  - no draft or unconfirmed profile can enter a Pipeline Run
  - derived claim traceability follows `claim -> evidence_refs -> evidence item -> source_refs -> source document`
  - canonical facts remain SSOT; runtime projection is derived and never becomes a second editable profile

## Required Outcomes

### Outcome: One Canonical Profile

- affected actor or system: Candidate Profile ingestion and persistence
- required result: each confirmed staged creation produces one immutable, validated `candidate-profile.v2` revision independent of source format
- success condition: downstream stages consume only the canonical revision and never branch on Markdown, DOCX, or YAML origin

### Outcome: User-Gated Creation

- affected actor or system: non-technical user, Candidate Profile workspace, and profile-attempt lifecycle
- required result: baseline facts and evidence require explicit approval before derivation; derived claims require explicit approval before final confirmation
- success condition: only Step 4 confirmation creates a pipeline-selectable canonical revision

### Outcome: Complete Workspace Integration

- affected actor or system: Candidate Profiles workspace, creation pages, Candidate Details, Run creation, Settings, and control-plane API
- required result: every visible page state and user action binds to one canonical API operation, server-owned capability, revision, fingerprint, and error contract
- success condition: deep links and refresh resume exact server state, stale edits never overwrite newer drafts, confirmation and details render identical `profile.canonical`, and Run creation lists only server-declared usable profiles

### Outcome: Deterministic-First Parsing

- affected actor or system: Markdown/DOCX extraction and LLM runtime
- required result: deterministic parsers own bytes, source blocks, locators, obvious structure, and normalization; LLM handles only ambiguous mapping and controlled derivation
- success condition: LLM never receives DOCX binary, never creates canonical IDs, and may be skipped when deterministic Step 2 mapping is complete

### Outcome: Uniform Evidence Projection

- affected actor or system: CV analysis evidence retrieval and selection
- required result: every nested canonical evidence statement becomes one `candidate-evidence.v1` item through the same projector
- success condition: source section and evidence kind are provenance metadata, not separate collector implementations or scoring bonuses

### Outcome: Complete Traceability

- affected actor or system: users, diagnostics, generated CV claims, and audit surfaces
- required result: every projected evidence item resolves to at least one verified uploaded source document, declared provenance remains distinguishable, and every derived skill claim resolves to at least one evidence item unless explicitly marked unsupported
- success condition: all reference chains resolve within the same immutable profile revision and can identify the original uploaded bytes

### Outcome: Education Symmetry

- affected actor or system: candidates with thesis, academic project, seminar, course, or other education evidence
- required result: education evidence competes under the same relevance function and global selection budget as work and project evidence
- success condition: changing only a statement's parent section does not change its base relevance score when its text, linked skills, and contextual terms are otherwise equal

### Outcome: Backward-Compatible Pipeline Entry

- affected actor or system: existing v1 Candidate Profiles and stored profile revisions
- required result: one compatibility adapter projects existing v1 shapes into v2 semantics without requiring immediate user edits or rewriting historical revisions
- success condition: existing valid profiles remain selectable, while all new runtime evidence flows through the v2 projection contract

## Design Analysis

### Current State and Evidence

| Question | Evidence | Source | Confidence | Specification implication |
|---|---|---|---|---|
| What is current profile owner? | Candidate loader validates YAML/JSON mappings and required v1 sections. | `src/fitcv/candidate.py` | high | Canonicalization belongs at Candidate Profile ingestion, before pipeline stages. |
| What IDs currently resolve? | Parent IDs from experience, project, achievement, certification, and education form reference targets. | `src/fitcv/candidate.py` | high | v2 must narrow claim references to evidence-item IDs while adapting old parent references. |
| Which sections currently enter evidence retrieval? | Experience, project, and achievement only. | `src/fitcv/evidence.py` | high | Existing collector branches must converge on one projector. |
| Does source section affect scoring? | Current type weights and quotas privilege specific evidence types. | `src/fitcv/evidence.py` | high | Uniform projection must remove source-section authority from base relevance. |
| Can users upload common CV formats? | Candidate Profile creation currently rejects non-`.yaml` files and requires UTF-8 text. | `src/fitcv_cp/sqlite_store.py` | high | Upload decoding/parsing becomes an ingress adapter; persistence and pipeline contracts remain format-neutral. |
| Is prototype creation state backed by API? | Candidate Profile creation, confirmation, and details are currently simulated inside the standalone prototype rather than loaded from control-plane attempt/revision resources. | `docs/fitcv-settings-ui-prototype.html` | high | Integration needs explicit route, request, polling, conflict, and reconciliation ownership. |
| Is education already considered valid support? | Education parent IDs pass current dangling-reference validation. | `tests/test_candidate.py` | high | Education support extends existing reference intent rather than introducing a separate subsystem. |
| Can model-assisted parsing reuse shared runtime? | Shared runtime already supports JSON-schema responses, parse/validation stages, normalized failures, and persistable provenance. | `src/fitcv/llm_runtime.py` | high | Creation adds routing parts and task contracts, not a provider client. |
| Can current LLM Configuration API save Candidate Profile routes? | Prototype presents both task IDs, but `LlmConfigurationPatchRequest` currently accepts only enrichment, ranking, CV generation, and synonym tasks. | `docs/fitcv-settings-ui-prototype.html`, `src/fitcv_cp/app.py` | high | Existing shared LLM configuration schema/presentation must add both Candidate Profile task IDs. |
| Is a DOCX library already installed? | Project dependencies contain no DOCX parser. | `pyproject.toml` | high | Initial extractor uses standard-library ZIP/XML support instead of adding dependency. |

### Scope

- included behavior:
  - `candidate-profile.v2` identity, provenance, baseline facts, derived claims, and validation
  - Candidate Profile creation from UTF-8 Markdown, DOCX, and YAML files
  - deterministic Markdown/DOCX source-block extraction and safe YAML mapping
  - staged baseline review, derived-claim review, and final confirmation
  - complete frontend binding for upload, resumable drafts, review batching, source dialogs, regeneration, approval, confirmation, list/detail reconciliation, archive/restore, and Run selection
  - deep-link, refresh, Back/Forward, asynchronous processing, polling, retry, stale-state reconciliation, and pending-action behavior
  - canonical field-schema delivery to frontend and existing Settings integration for Candidate Profile LLM task routing
  - structured LLM assistance for ambiguous baseline mapping and controlled derivation
  - canonical-YAML self-provenance behavior inside the shared staged lifecycle
  - one runtime `candidate-evidence.v1` projection
  - uniform relevance, ordering, and selection semantics
  - v1 compatibility adaptation and mixed-version runtime behavior
  - failure diagnostics required to prevent silent data loss
  - source-artifact retention and purge behavior for confirmed, failed, and abandoned attempts
- affected boundaries:
  - upload validation and source retention
  - Markdown/DOCX parser or YAML canonical-profile mapper
  - Candidate Profile attempt, draft, review, confirmation, and revision lifecycle
  - shared LLM runtime routing and provenance
  - Candidate Profile revision persistence
  - Candidate Profiles workspace, creation routes, details page, Run Candidate Profile picker, and LLM configuration page
  - profile validation and reference integrity
  - CV analysis evidence projection and selection
  - generated-CV evidence traceability
- admissible cases:
  - experienced candidate with only work evidence
  - fresh graduate with only education evidence
  - candidate with work, education, portfolio projects, achievements, certifications, or volunteering in any combination
  - clearly structured and ambiguously structured Markdown or DOCX CV
  - DOCX content in paragraphs, tables, headers, or footers
  - user-authored v1 or v2 YAML
  - parser-created canonical profile from Markdown or DOCX
  - empty optional sections and an inspectable review draft with no selectable evidence; confirmation remains blocked
- compatibility expectation: current valid v1 profiles remain runnable through one adapter; no pipeline consumer requires source-format-specific behavior.

### Non-Goals

- visual CV editor outside staged baseline and derived review
- PDF, plain-text, legacy binary `.doc`, `.docm`, rich-text, image, or archive CV ingestion
- OCR and image interpretation
- external credential verification or factual truth verification
- automatic merging of different uploaded CVs into one revision
- changing job ingestion, ranking, or user search-preference semantics
- making parser confidence a proficiency score or employment-verification score
- offline editing, collaborative multi-user merge, WebSocket/SSE delivery, or optimistic lifecycle transitions
- frontend-owned copies of canonical field definitions, validation rules, lifecycle guards, capabilities, or Candidate Profile canonical data

### Requirements and Behavioral Contract

#### Requirement: Canonical Profile Layers

- trigger or actor: successful ingestion of any supported source
- preconditions: source passes upload safety checks and parser/importer can produce a structurally valid profile
- required behavior: persisted profile separates four semantic layers:
  1. source documents: immutable typed metadata distinguishing verified uploaded bytes from unverified declared provenance
  2. baseline facts: candidate-authored or source-extracted profile content in natural sections
  3. derived claims: normalized skills or equivalent claims linked to evidence
  4. runtime projection: deterministic evidence items computed from canonical facts and claims
- output or state change: one immutable `candidate-profile.v2` revision plus ingestion diagnostics
- failure behavior: failed or incomplete canonicalization does not create an active usable revision; original upload metadata and safe failure diagnostics remain inspectable
- observable acceptance: no baseline fact is copied into a second editable top-level evidence store, and no runtime-only scoring field is written back as baseline truth

#### Requirement: Step 1 CV Creation Upload Boundary

- trigger or actor: user uploads a candidate document for profile creation
- preconditions: supplied file claims Markdown, DOCX, or YAML media type
- required behavior:
  - creation accepts `.md` with UTF-8 text, `.docx` with valid Office Open XML package structure, and `.yaml` with UTF-8 text parsed by a safe loader
  - user defines required Candidate Profile display name at upload; this workspace metadata remains separate from canonical candidate Full name
  - before attempt creation, request validation rejects missing/blank Profile Name, empty bytes, bytes above configured limit, unsupported extension, and extension/declared-media mismatch
  - pre-attempt rejection returns the stable `4xx` error and creates no attempt, source row, retained artifact, or idempotency result that can later be mistaken for an accepted upload
  - after coarse request validation succeeds, filename sanitization, original-byte checksum, retained-byte persistence, source-document insertion, and attempt insertion occur atomically before asynchronous processing starts
  - extension, declared media type, and detected structure must agree
  - `.doc`, `.docm`, encrypted/corrupt DOCX, JSON, PDF, plain text, images, and archives are rejected with stable failure codes
  - embedded media, macros, external relationships, and remote links are never executed or fetched
  - YAML mapping is deterministic: v2 fields and valid IDs are preserved; v1 fields use the compatibility adapter; both produce the same baseline and derived review drafts as Markdown/DOCX
  - every supported format enters the same attempt states, review gates, validation, confirmation, persistence, and runtime projection path
- output or state change: one accepted upload creates an inspectable Candidate Profile creation attempt that owns original upload metadata and starts non-selectable
- failure behavior: coarse request failures create no attempt; safety, decoding, package, parsing, or mapping failures discovered after accepted-byte persistence transition the created attempt to non-retryable or retryable `failed` without draft or canonical revision
- observable acceptance: no unconfirmed creation attempt exposes `use_for_run: true`

#### Requirement: Deterministic Source Blocks

- trigger or actor: valid Markdown or DOCX upload
- preconditions: original bytes are retained by creation attempt
- required behavior:
  - Markdown extractor uses UTF-8 lines and recognizes headings, paragraphs, lists, and table rows without external parser dependency
  - DOCX extractor uses Python standard-library ZIP and XML support and reads document paragraphs, table cells, headers, and footers in deterministic order
  - extractor emits immutable source blocks containing stable internal `block_id`, normalized display text, block kind, ordinal, native locator, and source-document ID
  - stable block IDs derive from original checksum, source part, native locator, and normalized text; LLM output cannot choose or replace them
  - images and empty formatting-only blocks produce no textual source block
- output or state change: one immutable extraction snapshot and fingerprint become the only input to Step 2 mapping
- failure behavior: malformed XML, unsupported encryption, unsafe ZIP entry, decompression limit breach, or inconsistent package produces failed attempt
- observable acceptance: repeated extraction of unchanged bytes produces identical blocks, order, locators, and fingerprint

#### Requirement: Creation State Machine

- trigger or actor: upload, processor, or user review action
- preconditions: Candidate Profile creation attempt exists
- required behavior:
  - `creation_status` is one authoritative state from `uploaded`, `extracting_base`, `base_review`, `deriving`, `derived_review`, `ready_to_confirm`, `succeeded`, or `failed`
  - allowed forward path is `uploaded -> extracting_base -> base_review -> deriving -> derived_review -> ready_to_confirm -> succeeded`
  - processing failures enter `failed` with safe code, retryability, and preserved last valid draft
  - failed attempt records owning failed stage; retry returns only to that stage and cannot skip required approval
  - user approval and correction submissions require idempotency plus expected draft revision or fingerprint
  - archive lifecycle remains independent from creation status
  - `use_for_run` is true only when `creation_status == succeeded` and lifecycle is active
- output or state change: every attempt exposes current state, next allowed action, retry capability, and latest approved/draft fingerprints
- failure behavior: stale review submissions return revision conflict and never overwrite newer corrections
- observable acceptance: impossible transitions and duplicate confirmation cannot create multiple canonical revisions

#### Requirement: Front-End/Back-End State Ownership

- trigger or actor: user opens, refreshes, navigates, or mutates any Candidate Profile creation or details route
- preconditions: control-plane API and Candidate Profile field schema are available
- required behavior:
  - integrated admin routes are `/admin/candidate-profiles/create`, `/admin/candidate-profiles/create/{attempt_id}/baseline`, `/admin/candidate-profiles/create/{attempt_id}/derived`, `/admin/candidate-profiles/create/{attempt_id}/confirm`, and `/admin/candidate-profiles/{candidate_profile_id}`
  - standalone prototype hash routes map one-to-one to these admin routes but are not transport or persistence owners
  - URL owns attempt/profile identity and visible stage; refresh and Back/Forward reload server resources instead of replaying client lifecycle state
  - server owns attempt state, revision, fingerprints, drafts, approvals, validation, failure, capabilities, `next_action`, confirmation payload, canonical revision, and active/archived lifecycle
  - component-local state owns selected file before upload, unsaved ordered review operations, open dialog, request pending state, and focus restoration only
  - frontend loads canonical field schema instead of embedding field labels, descriptions, control types, requirement rules, evidence kinds, date grammar, or section order
  - server `capabilities` owns enabled/disabled actions and reason text; frontend never derives capability from `creation_status`
  - direct navigation to an unavailable stage loads attempt first, then follows server `next_action`; succeeded attempt opens returned Candidate Profile details
- output or state change: every rendered page is a projection of current API resource plus bounded component-local draft state
- failure behavior: missing attempt/profile shows stable not-found state; unavailable stage never renders stale cached draft as current truth
- observable acceptance: same URL after refresh renders same server state, and no browser-only creation state is required to resume

#### Requirement: Step 2 Baseline Facts and Evidence Review

- trigger or actor: deterministic source extraction completes
- preconditions: immutable source-block snapshot exists
- required behavior:
  - deterministic mapping owns obvious headings, field labels, list structure, table structure, whitespace, and date-format normalization
  - LLM task `candidate_profile_base_mapping` receives only bounded source blocks plus deterministic mapping hints and runs only when unresolved or ambiguous blocks remain
  - Step 2 may extract observable identity/contact data, natural parent metadata, dates, locations, baseline summary/headline text, and nested evidence statements
  - Step 2 must not infer skills, role families, domain tags, responsibility themes, employers, institutions, dates, technologies, metrics, or qualifications absent from source blocks
  - every proposed fact or evidence statement retains one or more block references and displays source excerpt, locator, extraction method, and ambiguity warning during review
  - review fields use canonical field metadata as UI SSOT for label, description, requirement state, control type, and date format
  - optional fields display `Optional`; one-of requirements display their shared requirement instead of falsely marking either field required
  - field-description help uses an `i` control, while provenance uses a distinct `Source` action
  - source locators are not repeated below fields; `Source` opens the source-evidence dialog containing excerpt and locator
  - evidence `kind` uses the canonical kind dropdown, and evidence `start`/`end` use the shared optional date grammar
  - user may accept, edit, or remove proposed content; submitted corrections are stored as review batches, not keystrokes
  - approval creates immutable approved-baseline snapshot and fingerprint
- output or state change: approved baseline becomes sole input to Step 3
- failure behavior: unresolved ambiguity may remain visible but cannot be silently converted into asserted fact; structural validation errors block approval
- observable acceptance: Step 3 cannot start before approved-baseline fingerprint exists

#### Requirement: Step 3 Derived Details Review

- trigger or actor: user approves Step 2 baseline
- preconditions: approved-baseline snapshot and fingerprint exist
- required behavior:
  - deterministic derivation first extracts exact explicit skill names and existing normalized values when unambiguous
  - LLM task `candidate_profile_derived_claims` receives only approved baseline facts/evidence and may propose normalized skills, role families, domain tags, and responsibility themes
  - LLM may normalize or infer only when proposal cites canonical evidence IDs and includes bounded confidence and origin
  - LLM cannot introduce new employers, institutions, dates, technologies, metrics, qualifications, or evidence text
  - application generates canonical claim IDs; LLM returns evidence references and semantic values only
  - user may accept, edit, reject, or add claims; edited/added claims use user-owned origin semantics
  - supported claims require evidence references; unsupported user assertions remain visible but cannot affect evidence score or generated CV claims
  - approval creates immutable approved-derived snapshot tied to exact approved-baseline fingerprint
- output or state change: approved derived claims become eligible for final confirmation
- failure behavior: LLM failure preserves approved baseline and any last valid unapproved derived draft; retry never mutates approved baseline
- observable acceptance: every supported derived claim resolves to approved Step 2 evidence

#### Requirement: Upstream Edit Invalidation

- trigger or actor: user edits or replaces approved Step 2 content after derivation starts
- preconditions: derived draft or approved-derived snapshot exists
- required behavior:
  - any approved-baseline fingerprint change invalidates entire derived draft and approval
  - system returns to `base_review`; user must approve new baseline and rerun Step 3
  - previously reviewed derived data may remain inspectable as stale audit evidence but cannot be merged automatically
  - rerunning Step 3 after user edits requires explicit discard of edited derived draft
- output or state change: no derived claim survives against a different baseline fingerprint without fresh review
- failure behavior: stale derived approval or confirmation is rejected
- observable acceptance: final profile never combines baseline and derivation from different fingerprints

#### Requirement: Step 4 Confirm and Save

- trigger or actor: user approves Step 3 and confirms final profile
- preconditions: approved baseline and derived snapshots share same baseline fingerprint
- required behavior:
  - confirmation combines approved baseline, approved derived claims, ingestion-owned provenance, and user-owned `search_preferences`
  - confirmation displays Profile Name as read-only workspace metadata captured in Step 1 and never edits canonical candidate Full name
  - final validator checks required fields, global ID uniqueness, dates, confidence bounds, `evidence_refs`, `source_refs`, and at least one runnable evidence item
  - confirmation displays revision summary, approval/readiness checks, and a complete expandable preview of approved baseline and derived fields before save
  - confirmation uses the same details-page heading, collapsible section, details-grid, baseline preview, and derived preview components as Candidate Details and Run Details; no confirmation-only summary or checklist owns duplicate presentation logic
  - one successful confirmation creates first immutable `candidate-profile.v2` revision and changes attempt to `succeeded`
  - confirmation records canonical checksum plus deterministic parser and LLM runtime provenance
  - drafts, ambiguity warnings, review events, LLM responses, scores, and review-state fields remain outside canonical profile
- output or state change: confirmed profile becomes selectable for Pipeline Runs
- failure behavior: validation failure returns attempt to appropriate review step without creating partial canonical revision
- observable acceptance: repeated idempotent confirmation returns same profile revision

#### Requirement: Shared LLM Runtime Boundary

- trigger or actor: ambiguous Step 2 mapping or Step 3 controlled derivation needs model assistance
- preconditions: configured routing exists for requested task
- required behavior:
  - both tasks use existing `src/fitcv/llm_runtime.py` with `response_mode: json_schema`
  - `config/runtime/control_plane.yaml` owns routing parts `candidate_profile_base_mapping` and `candidate_profile_derived_claims`
  - LLM receives text blocks or approved structured baseline only, never DOCX binary, filesystem paths, credentials, or unbounded source content
  - request builder enforces model-input budget at block boundaries and fails visibly instead of truncating; batching is outside initial scope
  - output parser and validator reject unknown fields, dangling block/evidence refs, invalid confidence, and forbidden inferred fact classes
  - runtime evidence records model, route, adapter, attempts, latency, response identifiers, and normalized failure
  - no Candidate Profile-specific provider client, retry loop, credential lookup, or wire fallback is added
- output or state change: validated proposals enter review draft, never canonical profile directly
- failure behavior: routing, adapter, parse, or validation failures preserve attempt and expose retryable/non-retryable state without leaking raw private content
- observable acceptance: all generative calls use shared runtime evidence contract and no parser path bypasses review

#### Requirement: Canonical Identity

- trigger or actor: canonical-profile importer or document parser
- preconditions: an input record, evidence statement, or derived claim is accepted
- required behavior:
  - `schema_version` is exactly `candidate-profile.v2`
  - every source document, parent record, evidence item, and derived claim has a non-empty stable `id`
  - IDs are globally unique within one profile revision
  - valid caller-supplied IDs in canonical YAML are preserved
  - parser-created IDs are deterministic for identical original bytes, parser version, source locator, and normalized extracted content
  - IDs are immutable inside a revision
- output or state change: references use IDs, never array positions, titles, names, or mutable display labels
- failure behavior: duplicate, blank, malformed, or ambiguous IDs reject canonicalization
- observable acceptance: reordering YAML arrays does not break any reference in an already-valid profile

#### Requirement: Required Canonical Surface

- trigger or actor: staged YAML mapper or Markdown/DOCX parser
- preconditions: input is intended to become a Candidate Profile revision
- required behavior:
  - v2 YAML requires `schema_version`, non-blank `name`, and at least one recognized evidence-bearing section
  - v2 YAML authors provide every parent, evidence, and derived-claim `id`; ingestion does not invent missing semantic IDs for an allegedly canonical document
  - uploaded `source_documents` and uploaded-file `source_refs` are ingestion-owned defaults and are not required from YAML author; supplied provenance is accepted only as declared metadata
  - absent optional list sections normalize to empty lists; absent `contact` and `search_preferences` normalize to empty mappings
  - parent records require these identity fields:

| Section | Required parent fields | Evidence behavior |
|---|---|---|
| `experiences` | `id`, `role`, `company` | `evidence` may be empty for display, but empty parent contributes no runtime evidence. |
| `education` | `id`, `institution`, and at least one of `degree` or `field` | Same shared `evidence` contract. |
| `projects` | `id`, `name` | Same shared `evidence` contract. |
| `achievements` | `id`, `title` | Same shared `evidence` contract. |
| `certifications` | `id`, `name`, `issuer` | Same shared `evidence` contract. |
| `volunteering` | `id`, `organization`, `role` | Same shared `evidence` contract. |

  - a profile requires at least one valid nested evidence item before it is eligible for Pipeline Run selection
  - `skills`, `role_families`, `domain_tags`, `responsibility_themes`, `languages`, `headline`, `summary`, `interests`, contact fields, dates, URLs, locations, tags, and search preferences are optional unless another active contract requires them for a specific output
- output or state change: importer emits one normalized canonical mapping with defaults applied before validation and persistence
- failure behavior: malformed required fields reject canonicalization; a structurally valid draft with no evidence remains inspectable in `base_review`, and confirmation returns `candidate_profile_no_evidence` without creating a Candidate Profile revision
- observable acceptance: non-technical users do not author hashes, parser metadata, runtime scores, or source locators for canonical YAML uploads

The executable v2 field registry in `src/fitcv/candidate.py` is the canonical field-contract SSOT. Parser/importer validation, final validation, persistence serialization, runtime projection, and `getCandidateProfileFieldSchema` consume that registry directly. The table below is its normative design description, not a second manually maintained runtime registry. `CandidateProfileFieldSchema.schema_revision`, checksum, and `ETag` derive from canonical JSON serialization of the executable registry.

| Field | Shape | Ownership and rules |
|---|---|---|
| `schema_version` | string | Required; exactly `candidate-profile.v2`. |
| `source_documents` | list | Ingestion-owned source metadata. |
| `name` | string | Required baseline identity fact. |
| `headline`, `summary` | string or null | Optional baseline profile text. |
| `contact` | mapping | Optional `email`, `phone`, `location`, `linkedin`, `github`, and `website`; unknown contact keys are rejected. |
| `experiences` | parent list | Natural fields: `id`, `role`, `company`, optional `company_url`, `location`, `start`, `end`, `source_refs`, and `evidence`. Current employment is represented only by `end: Present`; canonical v2 has no separate `current` flag. |
| `education` | parent list | Natural fields: `id`, `institution`, at least one of `degree` or `field`, optional `location`, `start`, `end`, `source_refs`, and `evidence`. |
| `projects` | parent list | Natural fields: `id`, `name`, optional `context`, `url`, `start`, `end`, `source_refs`, and `evidence`. |
| `achievements` | parent list | Natural fields: `id`, `title`, optional `issuer`, `date`, `url`, `source_refs`, and `evidence`. |
| `certifications` | parent list | Natural fields: `id`, `name`, `issuer`, optional `date`, `expires`, `credential_id`, `url`, `source_refs`, and `evidence`. |
| `volunteering` | parent list | Natural fields: `id`, `organization`, `role`, optional `location`, `start`, `end`, `source_refs`, and `evidence`. |
| `languages` | list | Each entry requires `id` and `name`; optional `level` and `source_refs`. Languages are baseline facts, not runtime evidence unless supported by nested evidence in an admissible parent. |
| `skills`, `role_families`, `domain_tags`, `responsibility_themes` | derived-claim lists | Every list uses the common derived-claim contract below. |
| `interests` | string list | Optional baseline facts; not runtime evidence. |
| `search_preferences` | mapping | Optional `target_role`, `role_families`, `location_types`, `locations`, `domains`, `seniority_target`, `exclude_contract_types`, and `exclude_experience_levels`; user-owned and never parsed as candidate evidence. |

Every canonical `start` or `end`, including nested evidence dates, is optional. A present value is exactly `YYYY-MM` or `Present`; lowercase `present`, year-only values, and invalid months are rejected. Empty UI values normalize to omitted/null canonical values. `end: Present` is the sole canonical current-period marker; compatibility inputs such as `current: true` normalize to it and are not persisted in v2.

No section alias is canonical. In particular, canonical output uses `experiences`, `company`, `field`, `start`, `end`, `name`, `level`, and nested `evidence`; `experience`, `organization` for employment, `field_of_study`, `period`, `current`, `value`, `proficiency`, `bullets`, `highlights`, and singular evidence `date` are compatibility inputs only. `current: true` maps to `end: Present`; contradictory legacy `current` and `end` values reject adaptation. A legacy evidence `date` maps deterministically to `start` with empty `end`.

Canonical field ownership:

| Layer | Fields | Owner |
|---|---|---|
| identity and provenance | `schema_version`, IDs, `source_documents`, `source_refs` | canonicalization boundary |
| baseline facts | identity, contact, natural parent metadata, nested evidence text | uploaded source plus user corrections |
| derived claims | normalized `skills`, `origin`, `confidence`, `evidence_refs` | parser/importer or explicit canonical author |
| user intent | `search_preferences` | user |
| runtime-only projection | scoring text, score, rank, selection reason, trimming | CV analysis runtime |

#### Requirement: Source Documents and Source References

- trigger or actor: successful upload ingestion
- preconditions: original bytes and safe filename are available
- required behavior:
  - `source_documents[]` records `id`, `origin`, safe `filename`, `media_type`, SHA-256 checksum, and `parser.name`/`parser.version`
  - `origin` is `uploaded` or `declared`: uploaded documents have checksums verified from retained bytes; declared documents are preserved inert metadata whose checksum syntax is validated but whose bytes are unavailable and unverified
  - `source_refs[]` contains `document_id` plus optional tagged `locator`
  - Markdown uses `locator.kind: markdown_lines` with one-based inclusive `start` and `end`
  - DOCX paragraph content uses `locator.kind: docx_paragraph` with `part` and one-based `paragraph`
  - DOCX table content uses `locator.kind: docx_table_cell` with `part` and one-based `table`, `row`, and `cell`
  - DOCX `part` is `document`, `header`, or `footer`
  - canonical YAML self-provenance may omit `locator` because canonical item ID identifies exact submitted statement
  - one statement spanning multiple locations uses multiple source references
  - source metadata is descriptive only; filenames, paths, URLs, or locators never authorize filesystem or network reads
  - only uploaded documents may expose source blocks, byte download, or verified-source capability; declared documents may expose metadata only
  - every evidence-bearing parent and every nested evidence statement resolves through at least one `source_ref` to an uploaded document; declared references may supplement but never replace that verified chain
- output or state change: baseline parent records and nested evidence statements retain provenance at their own fact grain
- failure behavior: unknown `document_id`, invalid locator range, or locator incompatible with declared media type rejects canonicalization
- observable acceptance: every projected evidence item resolves to at least one verified uploaded source document/checksum without trusting external path; declared metadata remains visibly unverified

#### Requirement: Canonical YAML Upload Provenance

- trigger or actor: user uploads `candidate-profile.v2` YAML
- preconditions: uploaded document parses as a mapping and satisfies canonical field rules other than ingestion-owned provenance defaults
- required behavior:
  - importer hashes original uploaded bytes and creates one source-document record for the uploaded canonical file
  - imported canonical file is marked `origin: uploaded`; existing valid supplied source documents are preserved as `origin: declared` unless they identify the same verified uploaded file
  - existing valid source references are preserved as declared provenance
  - every evidence-bearing parent and every evidence statement receives one reference to uploaded canonical document whether or not declared references already exist; duplicate equivalent refs normalize to one entry
  - injected canonical-file references require only `document_id`; evidence `id` identifies the exact canonical statement
  - importer records its identity under `parser.name` and `parser.version` like every other ingestion path
- output or state change: stored canonical revision may contain added provenance metadata, while source-document checksum continues to describe original uploaded bytes
- failure behavior: supplied dangling or contradictory references are rejected rather than silently replaced; declared metadata never grants source download or verification capability
- observable acceptance: every manually authored evidence chain reaches verified uploaded YAML bytes while preserving any valid declared earlier provenance separately

#### Requirement: Private Source Retention and Purge

- trigger or actor: accepted upload, attempt inactivity, confirmation, archive, or source access
- preconditions: source bytes and extracted private content exist under local data root
- required behavior:
  - source bytes, source blocks, review snapshots, and model-bound extracted content are private operational data and never enter repository, public fixtures, logs, or public documentation
  - unconfirmed attempt inactive for 30 days becomes terminal non-retryable `failed` with `candidate_profile_source_expired`; original bytes, source blocks, and review snapshots containing CV text are purged atomically, while safe filename, media type, byte length, checksum, timestamps, and failure diagnostics remain inspectable
  - every accepted user mutation or successful processing completion resets unconfirmed `source_purge_after` to 30 days after new `updated_at`; lease renewal alone does not extend retention
  - confirmed attempt retains uploaded bytes and source blocks while immutable Candidate Profile revision references attempt; archive does not purge source because historical profile and Run traceability remain valid
  - successful confirmation clears `source_purge_after` because confirmed-source lifetime is governed by immutable revision reference, not draft inactivity
  - hard deletion of confirmed Candidate Profile and revision is outside this feature; therefore confirmed-source purge is also outside this feature
  - source access after purge returns `410 candidate_profile_source_purged`; server capabilities expose source availability so UI never offers View Source for purged or declared-only document
  - existing private data-root backup policy remains backup SSOT; this feature adds no second backup mechanism, purged content enters no new backup, and older backup expiration follows existing backup retention
- output or state change: every attempt exposes source availability and, when unconfirmed, exact `source_purge_after`
- failure behavior: purge transaction either removes all private attempt content and records terminal metadata or rolls back without partial deletion
- observable acceptance: abandoned CV content does not remain indefinitely, while confirmed profile evidence remains traceable for lifetime of immutable revision

#### Requirement: Evidence-Bearing Parent Shape

- trigger or actor: parser/importer emits work, education, project, achievement, certification, or volunteering records
- preconditions: parent record contains a stable `id`
- required behavior:
  - each evidence-bearing parent uses the same `evidence` list
  - each evidence entry requires `id`, `kind`, non-blank `text`, and canonical `source_refs`
  - `title`, `start`, and `end` are optional evidence metadata
  - `start` and `end` use the same canonical `YYYY-MM` or `Present` grammar as parent periods
  - `kind` is one of `work_achievement`, `work_responsibility`, `thesis`, `seminar`, `course`, `academic_project`, `project_highlight`, `achievement`, `certification_proof`, or `volunteer_contribution`
  - review UI renders `kind` from this list as a dropdown; kind remains explanation/rendering metadata, not scoring authority
  - parent sections retain their natural metadata such as role/company, degree/institution, project name/URL, issuer, organization, dates, location, tags, and themes
  - parent metadata is not independently selectable evidence unless represented by a nested evidence statement
- output or state change: thesis, course, seminar, academic project, responsibility, work achievement, project highlight, certification proof, and volunteer contribution share one evidence grain
- failure behavior: unsupported evidence value types or blank evidence text reject canonicalization
- observable acceptance: adding a new `kind` does not require a new collector or relevance formula

#### Requirement: Common Derived-Claim Shape

- trigger or actor: deterministic derivation, LLM proposal, YAML mapper, or user review
- preconditions: a normalized skill, role-family, domain-tag, or responsibility-theme claim is retained
- required behavior:
  - every entry in `skills`, `role_families`, `domain_tags`, and `responsibility_themes` contains `id`, normalized `name`, `origin`, bounded `confidence`, `support_status`, and ordered unique `evidence_refs`
  - `origin` distinguishes at least `extracted_explicit`, `inferred`, and `user_asserted`
  - `confidence` describes extraction or derivation confidence only
  - `evidence_refs` target nested evidence-item IDs, never parent IDs
  - `support_status` is `supported` or `unsupported`; supported claims require at least one evidence reference
  - unsupported user assertions may be retained only with explicit `support_status: unsupported`; they remain visible but cannot contribute evidence-based score or generated CV claims
- output or state change: claim-to-evidence associations have one canonical owner in each claim's `evidence_refs`
- failure behavior: dangling refs, duplicate refs, invalid confidence, or a supported claim with no refs reject canonicalization
- observable acceptance: one shared review component and validator handle every derived-claim list; runtime evidence derives linked claim names by reversing `evidence_refs`

#### Requirement: Search Preferences Separation

- trigger or actor: user supplies job-search intent
- preconditions: profile may or may not contain CV-derived facts
- required behavior:
  - v2 stores user intent under `search_preferences`
  - search preferences are never parser-derived from source evidence without explicit user confirmation
  - search preferences never project into candidate evidence
  - v1 `preferences` maps to v2 `search_preferences` through compatibility adaptation
- output or state change: candidate facts and user intent remain separate SSOTs
- failure behavior: absent preferences use existing pipeline defaults; absence does not invalidate factual evidence
- observable acceptance: changing target role or location preference does not alter canonical evidence IDs or provenance

#### Requirement: Uniform Runtime Projection

- trigger or actor: pipeline loads a validated profile revision for CV analysis
- preconditions: profile is v2 or has been adapted from valid v1
- required behavior:
  - projector walks every nested `evidence` entry from every admissible evidence-bearing section
  - each entry produces exactly one `candidate-evidence.v1` item
  - projection preserves `evidence_id`, `kind`, `title`, `text`, `source_section`, `parent_id`, and `source_refs`
  - projection adds normalized parent context through common optional fields: `parent_title`, `organization`, `location`, `start`, `end`, `role_family`, `domain_tags`, and `responsibility_themes`
  - projection derives `skills` from canonical skill claims whose `evidence_refs` contain the evidence ID
  - projection computes scoring text from evidence text, title, derived skills, and normalized parent context
  - runtime score, rank, selection reason, and trimming output remain runtime fields and never become canonical profile facts
- output or state change: one ordered list of `candidate-evidence.v1` records
- failure behavior: projector fails closed on an invalid canonical revision; it never silently drops a malformed referenced item
- observable acceptance: pipeline code after projection has no section-specific collection branch

Canonical runtime shape:

```yaml
schema_version: "candidate-evidence.v1"
evidence_id: "ev_edu_analytics_thesis"
kind: "thesis"
title: "Customer Churn Prediction"
text: "Built and evaluated classification models..."
source_section: "education"
parent_id: "edu_analytics_msc"
parent_title: "M.Sc. Business Analytics"
organization: "Example University"
location: "Germany"
start: "2024-10"
end: "Present"
role_family: null
domain_tags: []
responsibility_themes: []
skills:
  - "Machine learning"
  - "Statistical analysis"
source_refs:
  - document_id: "doc_cv_1"
    locator:
      kind: "docx_paragraph"
      part: "document"
      paragraph: 14
```

#### Requirement: Uniform Relevance and Selection

- trigger or actor: CV analysis compares candidate evidence with one job context
- preconditions: uniform evidence projection succeeds
- required behavior:
  - all evidence items use one relevance function over the same projected fields
  - `source_section`, parent type, and `kind` do not add or subtract base relevance
  - one global selection budget applies after relevance scoring
  - deterministic tie order uses `evidence_id`
  - source-section diversity may be reported diagnostically but cannot reserve quotas or displace a more relevant item
  - unsupported claims do not add linked skills or score
- output or state change: selected evidence can contain any mix of admissible source sections, including education-only output
- failure behavior: no evidence produces a valid empty selection with explicit `no_candidate_evidence`; it does not fall back to unrelated profile summary text
- observable acceptance: two otherwise identical evidence items from different source sections receive equal base scores

#### Requirement: V1 Compatibility Adapter

- trigger or actor: runtime loads a profile without `schema_version: candidate-profile.v2`
- preconditions: profile satisfies current v1 validation
- required behavior:
  - adapter maps `preferences` to `search_preferences`
  - each experience bullet becomes one evidence statement under its experience parent
  - project `business_value` and each project highlight become evidence statements under the project parent
  - each achievement becomes one achievement parent with one evidence statement
  - education thesis summary, course, activity, seminar-like extension, and academic-project extension become education evidence when non-blank
  - certification and volunteering content become nested evidence when they contain usable proof text
  - old parent-targeting `evidence_refs` expand to all evidence items created under the referenced parent
  - generated adapter IDs are deterministic within the immutable v1 snapshot
  - adapter output is runtime-only unless user explicitly saves a new v2 revision
- output or state change: one valid v2-equivalent in-memory profile enters the shared projector
- failure behavior: an old reference whose parent creates no evidence remains unsupported and is reported; it is not redirected to an unrelated item
- observable acceptance: current v1 work/project behavior remains available while education content starts using the same downstream path

#### Requirement: Determinism and Revision Ownership

- trigger or actor: retry, resume, or repeated projection of the same immutable profile revision
- preconditions: canonical revision and projector policy version are unchanged
- required behavior:
  - canonicalization records `parser.name` and `parser.version`
  - runtime projection records projection schema version
  - mutable creation concurrency uses only attempt revision; snapshot identity and approval use immutable snapshot ID/fingerprint
  - processing output is accepted only from current unexpired claim ID and matching attempt revision
  - identical canonical input produces identical projected IDs, fields, order, and scoring text
  - immutable Run input identifies exact Candidate Profile revision and checksum
  - persisted selected-evidence artifacts are audit/cache projections, not editable profile owners
- output or state change: retries and resumes can reproduce evidence selection inputs
- failure behavior: incompatible schema or projector version fails visibly rather than guessing a conversion
- observable acceptance: projection fingerprint remains stable across repeated runs with unchanged profile and policy

### API Contract

This section is the canonical transport contract until implementation moves the same operations into executable OpenAPI and tests. `docs/api.md` continues to describe the currently implemented direct-YAML API and must be updated only when this contract is implemented.

#### Contract Conventions

- all JSON resources use the existing `{"data": ...}` envelope; collections also use existing `page` and `meta`
- stable IDs are opaque strings: `attempt_id`, `candidate_profile_id`, `profile_revision_id`, `source_document_id`, `source_block_id`, `snapshot_id`, `review_batch_id`, and `action_id`
- Candidate Profile creation, review, regeneration, approval, retry, confirmation, archive, and restore mutations require `Idempotency-Key`; replaying same operation and request returns stored result, while reuse with different input returns `409 idempotency_conflict`
- existing shared mutations outside Candidate Profile lifecycle retain their existing contract; specifically, `PATCH /llm-configuration` continues to use revision CAS without a new idempotency-header requirement
- creation attempt owns sole mutable integer `revision`; every attempt mutation requires `expected_revision` and returns incremented attempt revision plus `ETag`
- stage resources repeat current attempt revision for one-request reconciliation but do not own an independent CAS revision; immutable snapshots own `snapshot_id` and fingerprint instead
- immutable extraction, baseline, derived, confirmation, and canonical payloads expose SHA-256 fingerprints over canonical JSON
- server-owned `capabilities` and `next_action` determine available UI actions; clients never infer transitions from status strings
- processing operations return `202`; synchronous review mutations return `200`; first successful confirmation returns `201`
- timestamps are UTC ISO 8601 strings; clients format them but do not rewrite them

#### Resource Shapes

`CandidateProfileCreationAttempt` is mutable workflow metadata, not a Candidate Profile:

```json
{
  "attempt_id": "attempt_opaque",
  "profile_name": "Analytics Profile",
  "creation_status": "base_review",
  "revision": 4,
  "source_document": {
    "source_document_id": "doc_opaque",
    "original_filename": "candidate.docx",
    "media_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "byte_length": 48123,
    "checksum": "sha256",
    "source_available": true
  },
  "processing": {
    "stage": null,
    "claim_id": null,
    "attempt": 1,
    "lease_expires_at": null
  },
  "source_purge_after": "2026-09-01T12:00:05Z",
  "fingerprints": {
    "extraction": "sha256",
    "baseline_draft": "sha256",
    "approved_baseline": null,
    "derived_draft": null,
    "approved_derived": null,
    "confirmation": null
  },
  "failure": null,
  "next_action": "review_baseline",
  "capabilities": {},
  "created_at": "2026-08-02T12:00:00Z",
  "updated_at": "2026-08-02T12:00:05Z"
}
```

`BaselineReviewDraft` and `DerivedReviewDraft` use same review envelope:

```json
{
  "attempt_id": "attempt_opaque",
  "stage": "baseline",
  "revision": 4,
  "fingerprint": "sha256",
  "document": {},
  "annotations": {
    "/summary": {
      "origin": "llm_normalized",
      "source_block_ids": ["block_opaque"],
      "confidence": 0.88,
      "warnings": [],
      "regenerable": true
    }
  },
  "validation": {"field_errors": []},
  "capabilities": {}
}
```

The review-envelope `revision` always equals enclosing attempt revision. It is not snapshot-local revision. Snapshot identity is `snapshot_id` plus fingerprint, and approval binds exact snapshot fingerprint.

- baseline `document` contains only canonical baseline roots and ingestion-owned `source_documents`; derived `document` contains only canonical derived-claim roots
- annotation keys use canonical ID-addressed field paths, never array indexes; examples are `/experiences/{experience_id}/role`, `/experiences/{experience_id}/evidence/{evidence_id}/text`, and `/skills/{skill_id}/name`
- annotations are review metadata and never enter `candidate-profile.v2`
- `CandidateProfileConfirmation` exposes read-only `profile.canonical`, canonical checksum, approval fingerprints, readiness, and warnings; its `profile.canonical` object is the exact object persisted on confirmation
- `CandidateProfile` exposes catalog metadata plus immutable `profile.profile_revision_id`, `profile.revision`, `profile.checksum`, `profile.schema_version`, and `profile.canonical`
- Candidate Profile collection rows are server-derived summaries and do not own a second baseline or derived copy
- `CandidateProfileFieldSchema` exposes `schema_revision`, ordered sections, field metadata, collection/claim metadata, evidence-kind options, date grammar, and static validation requirements; context-dependent regeneration remains on draft annotations/capabilities

#### Operations

| Operation | Method and route | Input | Result and rules |
|---|---|---|---|
| `getCandidateProfileFieldSchema` | `GET /candidate-profile-field-schema` | optional `If-None-Match` | Returns immutable field/review metadata with checksum-backed `ETag`; frontend caches by schema revision and never copies this registry into page code. |
| `listCandidateProfiles` | `GET /candidate-profiles` | existing page/view/status/search contract | Returns confirmed Candidate Profile summaries and server capabilities. Creation attempts never appear in this collection. |
| `createCandidateProfileCreationAttempt` | `POST /candidate-profile-creation-attempts` | `multipart/form-data`: required `profile_name`, required `profile_file` | Coarse request failure returns stable `4xx` with no attempt. Accepted request atomically stores original bytes plus attempt/source rows, returns `202 CandidateProfileCreationAttempt`, then starts deterministic extraction. Markdown, DOCX, and YAML use same operation. |
| `listCandidateProfileCreationAttempts` | `GET /candidate-profile-creation-attempts` | existing page contract; optional `status` and `search` | Returns resumable non-terminal attempts and inspectable failures; `succeeded` attempts may be included only when explicitly filtered. |
| `getCandidateProfileCreationAttempt` | `GET /candidate-profile-creation-attempts/{attempt_id}` | none | Returns current status, revision, fingerprints, failure, capabilities, and next action. Processing responses may include `poll_after_ms`. |
| `downloadCandidateProfileSource` | `GET /candidate-profile-creation-attempts/{attempt_id}/source` | none | Returns original retained uploaded bytes with safe `Content-Disposition`, checksum-backed `ETag`, and `X-Content-Type-Options: nosniff`; purged source returns `410`, and declared metadata has no download route. |
| `getCandidateProfileSourceBlock` | `GET /candidate-profile-creation-attempts/{attempt_id}/source-blocks/{source_block_id}` | none | Returns bounded excerpt, block kind, native locator, source-document summary, and checksum; never returns unrelated source content. |
| `getCandidateProfileBaseline` | `GET /candidate-profile-creation-attempts/{attempt_id}/baseline` | none | Returns current baseline review draft only when capability allows inspection. |
| `patchCandidateProfileBaseline` | `PATCH /candidate-profile-creation-attempts/{attempt_id}/baseline` | `expected_revision`, ordered `operations[]` | Applies one atomic review batch. Operations are `add`, `replace`, or `remove` against ID-addressed canonical field paths. Editing an approved baseline invalidates all derived state. |
| `regenerateCandidateProfileBaseline` | `POST /candidate-profile-creation-attempts/{attempt_id}/baseline/actions/regenerate` | `expected_revision`, `targets[]` | `targets: ["*"]` regenerates every server-declared regenerable field; explicit paths regenerate only those fields. Non-regenerable identity and natural fact fields are preserved. Returns `202`. |
| `approveCandidateProfileBaseline` | `POST /candidate-profile-creation-attempts/{attempt_id}/baseline/actions/approve` | `expected_revision`, `expected_fingerprint` | Validates and records immutable approved baseline, then starts derivation and returns `202`. |
| `getCandidateProfileDerived` | `GET /candidate-profile-creation-attempts/{attempt_id}/derived` | none | Returns current derived review draft tied to exact approved-baseline fingerprint. |
| `patchCandidateProfileDerived` | `PATCH /candidate-profile-creation-attempts/{attempt_id}/derived` | `expected_revision`, ordered `operations[]` | Applies one atomic review batch using same ID-addressed operation grammar as baseline. Editing approved derived data removes derived approval. |
| `regenerateCandidateProfileDerived` | `POST /candidate-profile-creation-attempts/{attempt_id}/derived/actions/regenerate` | `expected_revision`, `targets[]` | Uses same `targets` contract; each generated claim remains separately editable and traceable through `evidence_refs`. Returns `202`. |
| `approveCandidateProfileDerived` | `POST /candidate-profile-creation-attempts/{attempt_id}/derived/actions/approve` | `expected_revision`, `expected_fingerprint`, `expected_baseline_fingerprint` | Records immutable approved derived snapshot and moves attempt to confirmation readiness. |
| `getCandidateProfileConfirmation` | `GET /candidate-profile-creation-attempts/{attempt_id}/confirmation` | none | Returns read-only confirmation only when approved baseline and derived fingerprints match. Uses same `profile.canonical` representation as Candidate Profile details. |
| `confirmCandidateProfileCreationAttempt` | `POST /candidate-profile-creation-attempts/{attempt_id}/actions/confirm` | `expected_revision`, `expected_baseline_fingerprint`, `expected_derived_fingerprint`, `expected_confirmation_fingerprint` | Final-validates and atomically inserts catalog row plus first immutable v2 revision. Same confirmed attempt and fingerprints always return same Candidate Profile. |
| `retryCandidateProfileCreationAttempt` | `POST /candidate-profile-creation-attempts/{attempt_id}/actions/retry` | `expected_revision` | Allowed only for retryable `failed` attempt; resumes recorded owning stage without skipping approval. Returns `202` when processing restarts. |
| `getCandidateProfile` | `GET /candidate-profiles/{candidate_profile_id}` | none | Returns Candidate Profile details. `profile.canonical` equals confirmed canonical object; no reconstruction from display summaries is allowed. |
| `listCandidateProfileRuns` | `GET /candidate-profiles/{candidate_profile_id}/runs` | existing page contract | Returns Runs bound to immutable revisions of this Candidate Profile for details-page traceability. |
| `archiveCandidateProfile` | `POST /candidate-profiles/{candidate_profile_id}/actions/archive` | existing `expected_revision` contract | Changes catalog lifecycle only; immutable canonical revision remains unchanged. |
| `restoreCandidateProfile` | `POST /candidate-profiles/{candidate_profile_id}/actions/restore` | existing `expected_revision` contract | Symmetric inverse of archive. |
| `getLlmConfiguration` | `GET /llm-configuration` | optional `If-None-Match` | Existing shared operation must include both Candidate Profile tasks and eligible validated models. |
| `patchLlmConfiguration` | `PATCH /llm-configuration` | existing `expected_revision`; task changes | Existing shared operation accepts `candidate_profile_base_mapping` and `candidate_profile_derived_claims`; no parallel settings route. |

`operations[]` values are validated against executable canonical field registry. Canonical semantic IDs use `^[A-Za-z][A-Za-z0-9._-]{0,127}$`; `/` and `~` are forbidden, so an ID is one unescaped path segment. Braces in examples denote placeholders and are not sent literally: `/experiences/exp_1/role` is valid, while `/experiences/{experience_id}/role` is documentation notation.

- `add` targets collection root such as `/experiences` or `/experiences/exp_1/evidence`; value contains complete new entry including caller-supplied stable ID
- `add` fails `duplicate_id` when ID already exists and never replaces existing entry
- `replace` targets existing scalar, mapping, collection entry, or nested field by canonical ID-addressed path
- `remove` targets existing optional field or collection entry; removing required field or final evidence required for confirmation yields validation error
- `replace` or `remove` against missing target fails atomically with `invalid_value`; no operation batch is partially applied
- application generates IDs for parser/LLM proposals; frontend generates compliant IDs for explicit user-added entries and retains them through retry

Backend may coalesce UI edits into one review batch but never persists keystrokes as independent truth.

### Front-End/Back-End Integration Contract

#### Response Composition

- creation upload, regeneration, approval, retry, and confirmation return current `attempt` or confirmed `candidate_profile` inside existing `data` envelope; processing responses include `poll_after_ms`
- baseline and derived GET/PATCH responses return one stage resource containing current `attempt`, `draft`, `field_schema_revision`, and server capabilities; frontend needs no second request to reconcile successful mutation
- `candidate_profile_revision_conflict`, `candidate_profile_fingerprint_conflict`, and `candidate_profile_transition_invalid` include `data.current_attempt` and, when readable, `data.current_stage`; conflict recovery never depends on parsing error message text
- confirmation GET returns `attempt`, readiness/validation metadata, and `profile`; confirmation POST returns exact persisted Candidate Profile resource
- list endpoints return server summaries only; details endpoints return immutable `profile.canonical`

#### UI Operation Bindings

| UI surface or action | Canonical operation | Pending behavior | Success behavior | Failure behavior |
|---|---|---|---|---|
| Candidate Profiles page bootstrap | `getCandidateProfileFieldSchema`, `listCandidateProfiles`, `listCandidateProfileCreationAttempts` | keep page structure; skeleton confirmed rows and draft rows separately | render confirmed profiles and resumable/failed attempts as distinct resources | preserve any valid prior rows and retry failed query without combining resource types |
| Upload submit | `createCandidateProfileCreationAttempt` | lock Profile Name, file input, and submit; retain one idempotency key | navigate to baseline route using returned `attempt_id` and begin polling | preserve Profile Name and selected filename where browser permits; map file errors to upload controls |
| Creation route bootstrap | `getCandidateProfileCreationAttempt`, then current stage GET | keep stepper/heading; load current route only when capability permits | render stage from server resource or navigate to `next_action` | not-found returns workspace path; transient fetch error retains route and exposes retry |
| Save and exit | stage PATCH when local operations exist | lock footer actions while flushing one review batch | return to Candidate Profiles without approving or confirming | remain on stage with operations preserved; do not claim saved state |
| Add/edit/remove baseline entry | `patchCandidateProfileBaseline` | lock affected entry and stage approval, not unrelated navigation | replace stage resource with returned draft/revision | validation maps to paths; conflict enters explicit reconciliation |
| Regenerate all/one baseline field | `regenerateCandidateProfileBaseline` | lock declared targets and approval; preserve other draft values read-only | poll attempt until `base_review`, then reload baseline stage | retryable failure retains previous draft; non-regenerable target stays unchanged |
| Approve baseline | pending baseline PATCH, then `approveCandidateProfileBaseline` | flush local batch first; lock stage and footer | navigate to derived route and poll while `deriving` | patch failure blocks approval; approval validation stays on baseline |
| Add/edit/remove derived claim or `evidence_refs` | `patchCandidateProfileDerived` | same collection-level lock contract as baseline | replace stage resource with returned draft/revision | invalid evidence refs map to exact claim path; conflict enters same reconciliation |
| Regenerate all/one derived claim | `regenerateCandidateProfileDerived` | lock declared targets and approval; preserve approved baseline | poll until `derived_review`, then reload derived stage | preserve previous derived draft and expose retry capability |
| Approve derived | pending derived PATCH, then `approveCandidateProfileDerived` | flush local batch first; lock stage and footer | navigate to confirmation route | validation remains on derived; baseline fingerprint mismatch follows server `next_action` |
| Open field Source | `getCandidateProfileSourceBlock` | open accessible dialog shell with loading state | render bounded excerpt and locator; return focus on close | keep dialog open with retry; never substitute a different block |
| View Source | `downloadCandidateProfileSource` | disable invoking control until response headers arrive | download/open retained original bytes using server filename/media type | show artifact error without exposing local path |
| Confirmation bootstrap | `getCandidateProfileConfirmation` | render shared details sections as loading placeholders | render read-only server `profile.canonical` and readiness | stale state follows server `next_action`; persistence is not attempted |
| Confirm | `confirmCandidateProfileCreationAttempt` | lock primary action under one idempotency key | navigate to returned Candidate Profile details | retryable persistence failure keeps confirmation; exact replay opens existing profile |
| Candidate Details | `getCandidateProfile`, `listCandidateProfileRuns` | shared details sections use loading state | render returned `profile.canonical` unchanged and related Runs from server | preserve route and show retry/not-found state |
| Archive/restore | existing lifecycle operations | lock only affected action | reconcile returned metadata without changing canonical data | revision conflict reloads metadata and requires new action |
| Run Candidate Profile picker | existing Candidate Profile list | show loading/empty state | include only rows with `capabilities.use_for_run: true` | preserve selected ID only if refreshed row remains usable |

#### Review Batching and Idempotency

- frontend generates one idempotency key when user initiates a mutation and retains it through network retry until terminal response
- changed request content always uses a new key; repeated click, timeout retry, or lost response reuses original key
- text edits remain local until blur, collection add/remove, stage navigation, Save and exit, regeneration, or approval; one ordered batch is sent, never one request per keystroke
- approval first flushes pending stage batch and then uses returned revision/fingerprint; approval cannot race unsaved edits
- stage navigation with failed flush remains blocked unless user explicitly discards local operations
- only affected entries/actions are locked where safe; stage-wide approval and regeneration remain locked during any pending stage mutation

#### Asynchronous Processing and Polling

- frontend polls `getCandidateProfileCreationAttempt` only while server status is `uploaded`, `extracting_base`, or `deriving`, or after retry returns another processing status
- client honors bounded server `poll_after_ms`; absent value defaults to two seconds; transient network failures use capped backoff without changing attempt state
- polling stops when state changes to review, ready, succeeded, failed, or route identity changes
- background-tab polling may pause; visibility restoration triggers immediate refresh before enabling any action
- last valid stage draft remains visible read-only during regeneration; client never predicts generated values or progress percentage
- no WebSocket, SSE, client timer simulation, or optimistic lifecycle transition is required for initial integration

#### Processing Claim and Crash Recovery

- each processing transition atomically records `processing_stage`, opaque `processing_claim_id`, `processing_attempt`, and UTC `lease_expires_at` on attempt
- worker claim and completion use attempt revision CAS; completion also requires matching claim ID, so stale or duplicate worker cannot publish snapshot
- active worker renews bounded lease while processing; polling never renews lease
- application startup and existing periodic reconciliation mechanism scan processing attempts whose lease expired
- expired claim transitions attempt to retryable `failed` with `candidate_profile_processing_abandoned`, recorded `failed_stage`, and recorded `resume_status`; last valid snapshots and approvals remain unchanged
- initial version does not silently auto-requeue abandoned Candidate Profile processing; server exposes retry capability and user retry creates new processing claim
- processing state without unexpired lease is invalid and must be reconciled rather than polled forever

#### Stale-State Reconciliation

- frontend retains loaded stage fingerprint, loaded document, and ordered local operations until mutation succeeds or user discards them
- on revision/fingerprint conflict, response current stage becomes server truth; local operations remain separate and are not silently replayed
- UI marks an operation conflicting when target path changed since loaded document, target ID disappeared, or collection insertion ID now exists
- user may explicitly reapply valid non-conflicting operations as a new batch, edit conflicting values, or discard all local operations
- baseline conflict or edit that invalidates derivation clears derived routes from usable navigation according to returned capabilities; client keeps no hidden accepted-derived copy
- browser Back/Forward changes visible route only and never attempts reverse state transition

#### Settings and Runtime Routing Integration

- existing `GET/PATCH /llm-configuration` exposes routing parts `candidate_profile_base_mapping` and `candidate_profile_derived_claims`; request validation and task presentation registries must add both IDs once, from shared task metadata
- no Candidate Profile-specific provider, credential, model registry, or settings endpoint is added
- each actual processing/regeneration action resolves effective route at call start and records shared runtime evidence; retry may use newly saved Settings but produces a new reviewed snapshot/fingerprint
- deterministic extraction and already saved user corrections remain available when LLM route is unavailable
- `candidate_profile_llm_unavailable` action may link to LLM Configuration; frontend never embeds provider-specific remediation

#### Confirmed Profile Reconciliation

- Candidate Profiles page lists creation attempts separately from confirmed Candidate Profiles; draft or failed attempts never satisfy Run selection
- confirmation `profile.canonical` and saved details `profile.canonical` must be canonical-JSON equal and share confirmation checksum
- frontend writes no Candidate Profile row optimistically; confirmed row appears from POST response or next server list read
- archive/restore changes catalog lifecycle and capabilities only; details and historical Run snapshots retain same profile revision/checksum

### Persistent Data Model

| Model | Grain and mutability | Required ownership |
|---|---|---|
| `candidate_profile_creation_attempts` | one mutable row per accepted upload workflow | Owns Profile Name, sole CAS revision, creation status, failure/resume state, current snapshot pointers, fingerprints, parser identity, processing stage/claim/attempt/lease, source availability/purge deadline, timestamps, and terminal `candidate_profile_id`; never owns canonical profile JSON. |
| `candidate_profile_source_documents` | one immutable row per verified uploaded file | Owns sanitized filename, detected media type, byte length, original checksum, retained artifact locator or bytes, upload safety diagnostics, and purge timestamp. Declared YAML source metadata remains inside canonical revision and does not create operational source row. |
| `candidate_profile_source_blocks` | one immutable row per deterministic extracted block | Owns block ID, document ID, kind, ordinal, native locator, normalized text, extractor version, and extraction fingerprint. |
| `candidate_profile_baseline_snapshots` | append-only snapshot per accepted baseline mutation or regeneration | Owns `snapshot_id`, baseline JSON, review annotations, resulting attempt revision, fingerprint, extraction fingerprint, origin, and approval timestamp when approved. Attempt points to current draft and approved snapshot IDs. |
| `candidate_profile_derived_snapshots` | append-only snapshot per accepted derived mutation or regeneration | Owns `snapshot_id`, derived JSON, review annotations, resulting attempt revision, fingerprint, exact approved-baseline fingerprint, origin, and approval timestamp when approved. |
| `candidate_profile_review_batches` | append-only user or regeneration action | Owns stage, ordered operations or targets, actor/origin, prior and resulting attempt revisions/fingerprints, idempotent `action_id`, and timestamp; raw keystrokes are not stored. |
| shared LLM runtime evidence | append-only existing `llm_runtime_evidence_v1` record per actual model call | Owns route/model/adapter/attempt/latency/response/failure provenance. Candidate Profile tables reference it; they do not copy provider payloads or credentials. |
| `candidate_profiles` | one mutable catalog row per confirmed logical profile | Owns Profile Name, active/archived lifecycle, current immutable revision pointer, nullable related-attempt ID for grandfathered v1 rows, revision counter, timestamps, and server-derived capabilities. |
| `candidate_profile_revisions` | one immutable row per confirmed canonical revision | Owns exact canonical profile JSON, checksum, schema version, parser provenance, approval fingerprints, and nullable creation-attempt ID for grandfathered v1 revisions. First staged confirmation creates revision `1`; later editing/versioning is outside this feature. |
| existing `idempotent_actions` | one durable reservation/result per Candidate Profile mutation and key | Owns request fingerprint, operation scope, stored response, and replay semantics; shared LLM Configuration keeps its existing revision-only mutation contract. |

Foreign keys and uniqueness enforce at most one verified uploaded source document per initial attempt, globally unique IDs within each canonical revision, one first revision per confirmed attempt, and no attempt deletion while revision references it. Database foreign keys enforce Run profile/revision identity only. Run-creation transaction checks current profile is succeeded and active before inserting new `run_inputs`; later archive preserves existing historical Run references and snapshots. Snapshot JSON remains private operational data; only confirmed revision is pipeline input.

### Error Contract

All failures use existing actionable envelope. `field_errors[].field` uses canonical ID-addressed paths when error belongs to profile content. `4xx` upload errors raised before asynchronous acceptance create no attempt. After `202`, processing failures are stored under `attempt.failure` and polling GET remains `200`; same stable codes may be returned directly when a synchronous retry or review request detects condition.

| HTTP | Stable code | Retryable | Meaning and required action |
|---|---|---:|---|
| `404` | `candidate_profile_attempt_not_found` | no | Attempt ID does not exist; return to Candidate Profiles. |
| `404` | `candidate_profile_source_not_found` | no | Source document or block is absent from this attempt; refresh attempt and report integrity failure if reference remains. |
| `410` | `candidate_profile_source_purged` | no | Retained bytes or source block passed purge deadline; keep safe attempt metadata and remove source action. |
| `410` | `candidate_profile_source_expired` | no | Inactive unconfirmed attempt reached purge deadline and cannot resume, regenerate, approve, or confirm. |
| `409` | `candidate_profile_transition_invalid` | no | Operation is not allowed from current state; response `data` includes refreshed attempt. |
| `409` | `candidate_profile_revision_conflict` | no | `expected_revision` is stale; preserve unsaved UI values, reload draft, and require explicit reconciliation. |
| `409` | `candidate_profile_fingerprint_conflict` | no | Submitted baseline, derived, or confirmation fingerprint is stale or mismatched; reload owning stage. |
| `409` | `candidate_profile_already_confirmed` | no | Attempt already produced a profile but request does not match stored confirmation; open existing Candidate Profile. Exact replay returns resource without error. |
| `409` | `idempotency_conflict` | no | Same key was reused with different request content; generate a new key only for a new user action. |
| `413` | `candidate_profile_file_too_large` | no | Uploaded bytes exceed configured limit. |
| `413` | `candidate_profile_model_input_too_large` | no | Bounded source blocks exceed current single-request model budget; attempt remains inspectable and no silent truncation occurs. |
| `415` | `candidate_profile_file_type_invalid` | no | Extension or declared type is unsupported. |
| `415` | `candidate_profile_file_media_mismatch` | no | Extension, media type, and detected structure disagree. |
| `422` | `validation_failed` | no | Request or canonical fields are invalid; `field_errors` identifies every actionable field. |
| `422` | `candidate_profile_file_empty` | no | Uploaded file contains no bytes. |
| `422` | `candidate_profile_file_unsafe` | no | DOCX/YAML safety policy rejected package entry, encryption, macro, external relationship, path, or unsafe structure. |
| `422` | `candidate_profile_file_corrupt` | no | Source cannot be decoded or parsed deterministically. |
| `422` | `candidate_profile_field_not_regenerable` | no | Target is factual/non-inferable or lacks required context; preserve value and explain prerequisite. |
| `422` | `candidate_profile_reference_invalid` | no | Source or evidence reference is missing, dangling, duplicate, cross-attempt, or wrong type. |
| `422` | `candidate_profile_no_evidence` | no | Confirmation has no runnable nested evidence; return to baseline review. |
| `502` | `candidate_profile_llm_output_invalid` | yes | Provider response failed schema or semantic validation; preserve last valid draft and allow regeneration retry. |
| `503` | `candidate_profile_llm_unavailable` | yes | Configured runtime route/provider is unavailable; preserve deterministic work and allow retry. |
| `504` | `candidate_profile_processing_timeout` | yes | Extraction or controlled derivation timed out; preserve last valid snapshot and allow retry. |
| `500` | `candidate_profile_processing_abandoned` | yes | Worker claim lease expired or process restarted before completion; reconciler preserved last valid state and exposed retry. |
| `500` | `candidate_profile_processing_failed` | yes | Internal parser/derivation processing failed after source validation. |
| `500` | `candidate_profile_persistence_failed` | yes | Confirmation transaction failed and created no catalog row or partial revision. |

Field-level codes include `required`, `invalid_value`, `unsupported_field`, `read_only`, `duplicate_id`, `missing_source_ref`, `missing_evidence_ref`, `date_order_invalid`, `confidence_out_of_range`, and `one_of_required`. Error messages never echo unnecessary CV content, provider payloads, local paths, or credentials.

### State Transition Contract

| Current state | Trigger | Guard | Next state | Side effects |
|---|---|---|---|---|
| none | coarse upload validation fails | request is missing Profile Name, empty/oversized, unsupported, or media-mismatched | none | Return stable `4xx`; persist no attempt or source. |
| none | successful accepted-upload transaction | coarse-safe source and required Profile Name | `uploaded` | Atomically retain bytes, create attempt and immutable uploaded source-document row; no profile revision. |
| `uploaded` | processor claims attempt | expected attempt revision matches and no live claim exists | `extracting_base` | Increment attempt revision; record stage, claim ID, processing attempt, and lease before deterministic extraction/base mapping. |
| `extracting_base` | extraction/base mapping succeeds | immutable extraction fingerprint and valid baseline draft | `base_review` | Append source blocks and baseline snapshot; expose review. |
| `base_review` | patch baseline | expected revision matches and operations validate | `base_review` | Append review batch and baseline snapshot; invalidate prior baseline approval and all derived pointers. |
| `base_review` | regenerate baseline | expected revision matches and targets are allowed | `extracting_base` | Preserve current draft; process declared targets or all regenerable targets. |
| `base_review` | approve baseline | expected revision/fingerprint match and baseline validates | `deriving` | Freeze approved baseline snapshot and start controlled derivation. |
| `deriving` | derivation succeeds | output validates and cites current approved baseline evidence | `derived_review` | Append derived snapshot tied to approved-baseline fingerprint. |
| `derived_review` | patch derived | expected revision matches and operations validate | `derived_review` | Append review batch and derived snapshot; clear derived approval. |
| `derived_review` | regenerate derived | expected revision matches and targets are allowed | `deriving` | Preserve current derived draft and current approved baseline. |
| `derived_review` | approve derived | expected revision/fingerprints match and claims validate | `ready_to_confirm` | Freeze approved derived snapshot tied to approved baseline. |
| `ready_to_confirm` | patch derived after navigating back | expected revision matches | `derived_review` | Append derived snapshot and clear derived approval. |
| `derived_review` or `ready_to_confirm` | patch baseline after navigating back | expected revision matches | `base_review` | Append baseline snapshot; clear baseline approval and all derived draft/approval pointers. |
| `ready_to_confirm` | confirm | all expected fingerprints match and final validation passes | `succeeded` | Atomically create one catalog row and immutable v2 revision, then link attempt. |
| processing state | retryable processing failure | failure normalized | `failed` | Record `failed_stage`, `resume_status`, safe error, and last valid snapshots. |
| processing state | processing lease expires | reconciliation confirms unchanged expired claim | `failed` | Record `candidate_profile_processing_abandoned`, failed stage, and resume state; preserve last valid snapshots. |
| `ready_to_confirm` | persistence failure | transaction rolled back | `failed` | Record `resume_status: ready_to_confirm`; no partial profile or revision. |
| `failed` | retry | failure is retryable and expected revision matches | recorded `resume_status` | Rerun only failed stage; never clear approved upstream snapshots. |
| non-succeeded attempt | 30-day inactivity purge | `updated_at` reached `source_purge_after` and no mutation/processing transaction is active | `failed` | Record `candidate_profile_source_expired`; atomically purge retained private source/drafts and disable retry/source capabilities. |

Additional rules:

- `uploaded`, `extracting_base`, `deriving`, and retry processing are server-driven; matching attempt revision plus processing claim ID is required to advance or publish result
- malformed user input before any valid draft may enter non-retryable `failed`; user must create a new attempt with corrected file
- confirm validation errors do not create a revision: baseline errors move to `base_review` and invalidate derived state; derived errors move to `derived_review`; fingerprint errors leave current state unchanged
- `succeeded` is terminal for creation; all creation mutation capabilities are false and archive/restore operate only on Candidate Profile lifecycle
- exact repeated confirmation, including a new idempotency key with same stored fingerprints, returns same Candidate Profile; one attempt cannot create two first revisions
- archive state never changes `creation_status`, fingerprints, canonical checksum, or Run snapshots
- archive prevents new Run selection but never invalidates existing `run_inputs` or historical Run snapshots

### Constraints and Alternatives

- constraint: source code and tests remain runtime authority until this proposed specification is implemented and verified
- constraint: private uploaded CV content and provenance must not enter public sample or generated public documentation
- constraint: upload boundary must retain existing filename sanitization and byte limits; coarse rejects remain on Upload, while accepted uploads retain inspectable asynchronous safety/parsing failures
- alternative: one-shot LLM conversion from uploaded CV directly to canonical profile
  - benefit: smallest visible workflow and one model call
  - trade-off: combines extraction with inference, weakens correction provenance, and permits unreviewed hallucination into pipeline truth
  - reason accepted or rejected: rejected because final profile must be approved in two semantically distinct review gates
- alternative: deterministic-only Markdown/DOCX conversion
  - benefit: cheapest, reproducible, and model-independent
  - trade-off: cannot reliably map ambiguous layouts or produce controlled normalized/inferred claims
  - reason accepted or rejected: retained as first processing layer but rejected as complete creation path
- alternative: staged deterministic-first parser with controlled LLM assistance
  - benefit: preserves source fidelity, minimizes model authority, and aligns user review with baseline versus derived semantics
  - trade-off: adds draft states, approval fingerprints, and invalidation rules
  - reason accepted or rejected: accepted
- alternative: keep separate collectors and add an education collector
  - benefit: smallest immediate code diff
  - trade-off: preserves type-specific branches, quotas, and future section drift
  - reason accepted or rejected: rejected because it fixes one symptom without satisfying symmetry or permanence
- alternative: flatten all evidence into a top-level editable `evidence` array
  - benefit: simple runtime iteration
  - trade-off: duplicates or disconnects natural section context and creates a second authoring surface
  - reason accepted or rejected: rejected because nested facts remain SSOT and runtime flattening is sufficient
- alternative: let evidence items own copied skill names
  - benefit: simpler local scoring input
  - trade-off: duplicates the skill-evidence relationship and permits drift
  - reason accepted or rejected: rejected; projector derives reverse links from `skills[].evidence_refs`
- alternative: retain experience/project/achievement type bonuses and reserved quotas
  - benefit: preserves current selection bias
  - trade-off: disadvantages fresh graduates and violates equivalent-case treatment
  - reason accepted or rejected: rejected; source type remains explanatory metadata only

## Design Decisions

### Decision: Staged Hybrid Creation

- context: deterministic parsers are reliable for source extraction while ambiguous structure and semantic derivation need controlled model assistance
- selected approach: Step 1 upload, deterministic source blocks, Step 2 baseline review, Step 3 derived review, then Step 4 confirmation
- rationale: keeps facts, inference, and final authority separate while retaining one final canonical profile
- alternatives considered: one-shot LLM; deterministic-only conversion
- accepted trade-offs: users perform two approvals and upstream edits invalidate downstream review
- affected owners and boundaries: creation attempt owns drafts/review; canonical profile owns confirmed output; shared LLM runtime owns model transport

### Decision: Drafts Are Not Candidate Profile Revisions

- context: review metadata, ambiguity warnings, and LLM proposals are temporary and may be corrected or rejected
- selected approach: keep source blocks, drafts, fingerprints, review batches, and LLM evidence under creation attempt; create canonical revision only on confirmation
- rationale: prevents competing SSOTs and guarantees Pipeline Runs see approved data only
- alternatives considered: save one profile revision after each step
- accepted trade-offs: attempt storage must survive process restart independently from canonical revision table
- affected owners and boundaries: control-plane persistence owns attempt state; Candidate Profile revision remains immutable pipeline input

### Decision: Executable Registry Owns Field Contract

- context: parser, validator, projector, persistence, API metadata, and frontend must agree on fixed v2 fields without copying Markdown tables into code
- selected approach: `src/fitcv/candidate.py` owns one executable v2 field registry; field-schema API serializes same registry and this specification describes it normatively
- rationale: one executable owner prevents parser/UI/schema drift while retaining human-readable approved contract
- alternatives considered: Markdown table as runtime source; separate backend and frontend registries; generated code from specification text
- accepted trade-offs: registry checksum/revision changes whenever field contract changes and requires contract tests against this specification
- affected owners and boundaries: Candidate Profile domain owns registry; API exposes read-only projection; frontend owns no field definitions

### Decision: Attempt Owns CAS and Processing Lease

- context: attempt and stage-local revisions create ambiguous stale-write ownership, while asynchronous process exit can strand processing state
- selected approach: one attempt revision guards every mutation; snapshots are immutable; processing claim adds lease and claim ID reconciled by existing control-plane mechanism
- rationale: one concurrency owner covers baseline invalidation, derived invalidation, retry, and worker completion uniformly
- alternatives considered: independent stage revisions; database row locks held through processing; optimistic processing without recovery
- accepted trade-offs: unrelated accepted attempt mutations serialize through one revision and abandoned processing requires explicit user retry
- affected owners and boundaries: attempt table owns CAS/lease; reconciler owns expired-claim transition; snapshot tables own immutable history

### Decision: Natural Sections Own Facts; Projector Owns Flattening

- context: profile authoring and CV parsing need human-meaningful sections, while scoring needs one evidence grain
- selected approach: persist nested evidence under natural parent sections and derive a flat runtime projection
- rationale: preserves SSOT and context without making pipeline logic section-specific
- alternatives considered: top-level editable evidence store; separate section collectors
- accepted trade-offs: projector must attach normalized parent context at runtime
- affected owners and boundaries: Candidate Profile schema owns facts; evidence runtime owns derived projection

### Decision: Evidence Item Is Sole Scorable Grain

- context: parent records contain metadata and may contain several independently relevant statements
- selected approach: only nested evidence statements enter relevance scoring and selection
- rationale: thesis, course, responsibility, and project highlight become comparable atomic claims
- alternatives considered: score whole parent records; score both parents and children
- accepted trade-offs: v1 parents require deterministic expansion into child evidence
- affected owners and boundaries: canonicalizer or adapter creates evidence grain; selector consumes it

### Decision: Claims Reference Evidence, Evidence References Sources

- context: generated skills need semantic support and original-document provenance
- selected approach: use two typed reference edges: `evidence_refs` for claim support and `source_refs` for source provenance
- rationale: preserves a clear, non-circular trace chain with one owner per relationship
- alternatives considered: skills copied into evidence; direct skill-to-document references
- accepted trade-offs: validation must maintain two reference namespaces and runtime builds one reverse index
- affected owners and boundaries: Candidate Profile validator owns integrity; diagnostics render resolved chains

### Decision: Uploaded Source Is Verification Root

- context: user-authored YAML may include useful earlier provenance that cannot be verified against bytes uploaded in current attempt
- selected approach: importer creates verified uploaded source record for canonical bytes, preserves supplied sources as declared metadata, and attaches uploaded-source reference to every evidence-bearing fact
- rationale: every evidence chain reaches bytes system actually received without discarding user-declared history or granting it false verification capability
- alternatives considered: trust supplied checksums; discard supplied provenance; attach uploaded source only when refs missing
- accepted trade-offs: YAML evidence may carry both uploaded and declared references, and declared source has metadata-only UI
- affected owners and boundaries: upload attempt owns verified retained bytes; canonical revision owns uploaded/declared provenance; source API serves uploaded sources only

### Decision: One Section-Neutral Relevance Function

- context: current section weights and quotas make work history structurally stronger than education
- selected approach: score all `candidate-evidence.v1` items with one function and one global budget
- rationale: evidence content and linked skills determine relevance, not candidate career stage or section label
- alternatives considered: education-specific weight; career-stage switch; reserved per-section quotas
- accepted trade-offs: existing section-biased result ordering changes when equivalent education evidence is more relevant
- affected owners and boundaries: CV analysis policy owns relevance inputs and budget; profile schema owns no scoring policy

### Compatibility, Migration, and Risk

- old behavior: unversioned v1 YAML is primary input; skills may reference parent IDs; evidence collection branches by experience/project/achievement; education is not collected; uploads accept `.yaml` only
- new behavior: Markdown, DOCX, and YAML creation attempts require same staged review and confirmation before creating v2; claims reference evidence IDs; all evidence-bearing sections flatten through one projector
- compatibility boundary: existing stored v1 revisions remain immutable and use adapter at runtime; uploaded v1 YAML enters same staged creation lifecycle and produces v2 only after confirmation
- migration or backfill:
  - control-plane schema advances atomically from version `4` to version `5` through SQLite table rebuild where current checks or nullability cannot be altered in place
  - existing succeeded Candidate Profile rows preserve `candidate_profile_id`, lifecycle, catalog revision, default/sort metadata, timestamps, `profile_revision_id`, immutable profile JSON, checksum, schema revision, and every `run_inputs` foreign-key value
  - existing succeeded rows have nullable creation-attempt link because no historical staged attempt exists; no synthetic source bytes, approval fingerprints, or provenance are invented
  - existing null/blank Profile Name is grandfathered by persisting current display fallback once: sanitized original filename stem, otherwise `Unnamed profile`; duplicate Profile Names remain allowed
  - existing failed direct-upload profile rows leave confirmed catalog and become deterministic legacy failed-attempt records preserving original profile ID as migration source ID, filename, media type, byte length, checksum, timestamps, and safe failure diagnostics
  - migrated failed attempts are non-retryable, expose `source_available: false`, have no source-document/source-block rows because current schema retained no bytes, and cannot enter review or confirmation
  - migration copies/rebuilds within one transaction, validates counts, uniqueness, and `PRAGMA foreign_key_check`, then advances `user_version`; any failure rolls back and leaves version `4` readable without partial new tables
  - optional explicit save-as-v2 may create a new revision only after user enters current staged lifecycle and confirms; migration never rewrites historical v1 profile JSON
- rollout and rollback: staged creation UI/routes may be withdrawn while migrated catalog rows, immutable revisions, Run references, and v1 runtime adapter remain available; rollback never attempts destructive downgrade after new staged attempts exist
- deprecation or consumer impact: Candidate Profile API consumers must recognize expanded creation states and derived capabilities; direct consumers of parent-targeting `evidence_refs`, array-index `source_ref` strings, or section-specific evidence types must move to v2 contracts
- sample migration: `data/candidate_profile.v2.sample.yaml` must move from PDF/page provenance to Markdown or DOCX tagged locators when implementation begins
- risk:
  - parser invents unsupported facts
    - mitigation: Step 2 forbids inference; Step 3 requires evidence refs, confidence, and user approval
  - DOCX package causes resource exhaustion or unsafe external access
    - mitigation: ZIP entry/decompression limits, XML-only allowlist, no macro execution, and no relationship fetching
  - stale correction overwrites newer review
    - mitigation: idempotency plus expected revision/fingerprint on every review submission
  - baseline edit leaves accepted derivation attached to old facts
    - mitigation: whole derived snapshot invalidation on baseline fingerprint change
  - LLM failure loses deterministic extraction or user corrections
    - mitigation: attempts persist source blocks and last valid draft independently from LLM call
  - canonical YAML carries malicious paths or URLs
    - mitigation: provenance fields are inert metadata and never trigger reads
  - v1 expansion changes selection volume
    - mitigation: one global budget and deterministic relevance order bound output
  - new projector silently omits evidence
    - mitigation: acceptance compares canonical evidence count with projection count and fails on malformed items
  - frontend duplicates canonical field definitions or lifecycle rules
    - mitigation: field-schema API plus server capabilities/next action remain only UI contract owners
  - polling or repeated clicks create duplicate processing or confirmation
    - mitigation: server-provided poll interval, one pending request per operation, and durable idempotency replay
  - process exits while attempt is in server-driven processing state
    - mitigation: durable processing claim lease and startup/periodic reconciliation convert abandoned work to retryable failed state
  - legacy SQLite migration loses profile or Run identity
    - mitigation: transactional v4 migration preserves IDs and validates foreign keys/counts before version advance
  - declared YAML provenance is mistaken for verified uploaded bytes
    - mitigation: explicit uploaded/declared origin and mandatory uploaded-file source ref on every evidence-bearing fact
  - abandoned upload retains private CV content indefinitely
    - mitigation: 30-day inactive-attempt purge with safe metadata retention and no second backup owner
  - stale browser edits overwrite a newer review draft
    - mitigation: expected revision/fingerprint, conflict payload with current stage, and explicit path-level reconciliation
  - confirmation preview and Candidate Details drift
    - mitigation: both render same server-owned `profile.canonical` and checksum; frontend reconstruction is forbidden
  - private source content leaks into public fixtures
    - mitigation: public-safe sample remains synthetic and publication boundary remains enforced

## Invariants and Edge Cases

### Invariants

- one immutable Candidate Profile revision is canonical SSOT for candidate facts, provenance, derived claims, and search intent
- executable v2 field registry in `src/fitcv/candidate.py` is sole runtime field-contract owner; API and frontend consume projections of it
- creation attempts and drafts are never Pipeline Run inputs
- creation attempt owns sole mutable CAS revision; snapshots never own independent mutable revision
- Step 3 consumes one approved-baseline fingerprint; Step 4 consumes matching approved baseline and derived fingerprints
- LLM cannot create canonical IDs, source locators, baseline evidence text, or final profile revision
- DOCX binary never enters LLM request
- user confirmation is sole transition that creates first canonical revision
- one nested evidence entry produces exactly one runtime evidence item
- every projected evidence ID is globally unique and resolves back to one canonical evidence entry
- every `source_refs[].document_id` resolves to one source document in the same revision
- every evidence-bearing parent and nested evidence statement has at least one source reference to `origin: uploaded`; declared provenance alone never satisfies verified traceability
- every supported `skills[].evidence_refs[]` resolves to one nested evidence item in the same revision
- evidence items never own duplicated canonical skill lists
- runtime scoring fields never become baseline profile facts
- source section and evidence kind never alter base relevance
- canonicalization and projection are deterministic for unchanged inputs and versions
- original upload checksum always describes original bytes, not enriched canonical serialization
- canonical v2 stores no `current` flag; `end: Present` is sole current-period truth
- every processing state has one unexpired processing claim lease; expired claim reconciles to retryable failure
- archived profile remains referenced by historical Runs but cannot be selected for new Run
- coarse upload rejection creates no attempt; accepted upload failure never creates partial Candidate Profile revision
- search preferences never become evidence

### Edge Cases

- empty or minimal input: deterministic extraction with no meaningful text fails creation; identity/contact-only draft may be reviewed but cannot confirm until at least one valid evidence item exists
- clear Markdown input: deterministic Step 2 mapping may skip baseline LLM call and still requires user approval
- ambiguous Markdown or DOCX input: only unresolved blocks enter baseline LLM task; resolved deterministic mappings remain authoritative unless user edits them
- DOCX tables, headers, and footers: extractor preserves native tagged locator and deterministic order; embedded images remain unsupported
- normal and large input: projector emits one item per evidence statement and selector applies existing configured global limits; no per-section expansion limit silently drops canonical evidence before scoring
- duplicate, missing, malformed, or unsupported data: reject IDs outside canonical grammar, duplicate IDs, dangling refs, blank evidence text, invalid confidence, invalid hashes, incompatible locators, and unsupported file formats with stable failure codes
- retry, timeout, partial failure, crash, or concurrency: failed extraction/LLM never activates partial revision; expired worker lease becomes retryable failed state; retry resumes owning stage and preserves approved snapshots/user corrections; duplicate action is idempotent; stale action conflicts
- upstream correction after Step 3: entire derived snapshot becomes stale and confirmation remains disabled until new derivation is approved
- migration or mixed-version state: v1 and v2 revisions may coexist; both converge before evidence retrieval; migrated failed rows have no invented source bytes or retry capability; pipeline output records source profile schema plus effective projection schema
- generated-source consistency: parser/importer version and original checksum are recorded; all injected source refs target verified uploaded source-document record, while supplied historical provenance remains declared
- source expiry: inactive unconfirmed attempt purges private bytes, blocks resume/confirmation, retains safe diagnostics, and returns `410` for source access
- security or accessibility boundary: uploaded content is data, never executable configuration; YAML uses safe loading; archive/path traversal and remote dereference are forbidden; user-facing failures identify field/location without echoing unnecessary private content

## Validation Plan

### Acceptance Criterion: All Supported Inputs Converge

- setup or precondition: equivalent candidate content exists as Markdown, DOCX, and canonical YAML fixtures
- action: ingest each fixture
- expected result: each successful revision satisfies `candidate-profile.v2` and projects semantically equivalent evidence, claims, and provenance
- failure condition: downstream code branches on original format or equivalent facts disappear
- proof method: ingestion contract tests plus normalized projection comparison excluding source-format locator differences
- expected evidence: successful revisions, recorded checksums/parsers, and equivalent `candidate-evidence.v1` payloads

### Acceptance Criterion: Deterministic Source Extraction

- setup or precondition: Markdown fixture plus DOCX fixtures containing paragraphs, tables, headers, and footers
- action: extract each fixture twice
- expected result: blocks, order, IDs, locators, normalized text, and fingerprint are identical across runs
- failure condition: extraction depends on LLM, unstable ZIP/XML iteration, or mutable array positions outside native locator
- proof method: focused parser regression tests with one generated minimal DOCX fixture
- expected evidence: identical source-block snapshots and explicit rejection of corrupt/encrypted/unsupported inputs

### Acceptance Criterion: Step 2 Gate

- setup or precondition: valid extraction snapshot with deterministic and ambiguous blocks
- action: process baseline draft, submit corrections, and attempt derivation before and after approval
- expected result: deterministic facts remain, ambiguous proposals cite blocks, corrections persist, and derivation starts only after approved-baseline fingerprint exists
- failure condition: Step 2 infers forbidden facts, LLM overwrites deterministic mapping silently, or Step 3 starts from unapproved draft
- proof method: creation-state and baseline-task contract tests
- expected evidence: review draft, correction batch, approved fingerprint, blocked premature transition, and LLM runtime evidence when used

### Acceptance Criterion: Step 3 Controlled Derivation

- setup or precondition: approved baseline contains explicit and inferable evidence
- action: derive skills/tags, then accept, edit, reject, and add claims
- expected result: every supported claim cites evidence, forbidden baseline facts cannot appear, user edits preserve user-owned origin, and unsupported claims cannot score or generate CV claims
- failure condition: model creates evidence text/IDs or unsupported claim enters evidence-based output
- proof method: structured LLM parser/validator tests plus derived-review state test
- expected evidence: valid and rejected JSON-schema payloads, resolved evidence refs, and approved-derived fingerprint

### Acceptance Criterion: Upstream Edit Invalidates Derivation

- setup or precondition: approved baseline and approved derived snapshot exist
- action: change approved Step 2 fact or evidence and submit new baseline
- expected result: creation returns to `base_review`, derived snapshot becomes stale, and confirmation remains disabled until Step 3 reruns and is approved
- failure condition: stale claim reaches final canonical profile
- proof method: lifecycle regression test using mismatched fingerprints
- expected evidence: stale marker, rejected confirmation, and new matching fingerprints after rerun

### Acceptance Criterion: Confirmation Is Sole Save Boundary

- setup or precondition: approved baseline and derived snapshots share fingerprint
- action: confirm twice with same idempotency key, then inspect Candidate Profile resource
- expected result: one immutable v2 revision is created, both responses identify same revision, attempt becomes `succeeded`, and `use_for_run` becomes true
- failure condition: review step creates revision, duplicate confirmation creates another revision, or draft metadata enters canonical payload
- proof method: persistence/API idempotency test
- expected evidence: one revision row, canonical checksum, succeeded resource, and no draft/review fields in profile JSON

### Acceptance Criterion: Shared LLM Runtime Only

- setup or precondition: baseline ambiguity and derived-claim tasks require model calls
- action: execute both tasks with success, routing failure, parse failure, and validation failure responses
- expected result: calls use configured routing and `json_schema`; normalized runtime evidence records outcome; attempt remains recoverable on failure
- failure condition: custom provider client, raw DOCX bytes, unbounded content, or direct canonical persistence bypasses shared runtime/review
- proof method: shared-runtime integration tests with adapter stubs
- expected evidence: two routing parts, bounded requests, normalized failures, and unchanged approved snapshots

### Acceptance Criterion: Field Schema and Deep-Link SSOT

- setup or precondition: executable v2 registry has known revision and attempts are in upload, baseline review, derived review, confirmation-ready, failed, and succeeded states
- action: serialize field-schema API, validate representative documents through parser/final validator, then open each integrated admin route directly, refresh it, and use browser Back/Forward
- expected result: API metadata and validator behavior derive from same registry; frontend loads field metadata from `getCandidateProfileFieldSchema`, renders only server-permitted stage, and follows `next_action` when route is unavailable
- failure condition: Markdown table, API, parser, validator, projector, or page owns divergent field rule; page requires prior browser state or infers action availability from status
- proof method: executable-registry contract test plus frontend state tests and Playwright deep-link/refresh navigation
- expected evidence: matching schema revision/checksum, validation parity, identical route restoration, field-schema request, capability-driven controls, and no client-owned field/lifecycle table

### Acceptance Criterion: Review Batching and Stale Reconciliation

- setup or precondition: user has multiple unsaved baseline or derived edits while another accepted mutation advances server revision; batches also contain compliant add ID, duplicate add ID, missing replace target, and malformed ID
- action: flush review batch, receive revision conflict, reapply one unchanged-path operation, discard one conflicting operation, and submit each path/ID edge case
- expected result: no keystroke requests occur; server current stage becomes truth; local operations remain recoverable; compliant add succeeds once; duplicate, missing-target, and malformed-ID batches fail atomically with path-level errors
- failure condition: local edits disappear, stale batch overwrites current draft, client silently merges conflicting path, braces are treated literally, malformed ID becomes path segment, or failed batch partially mutates document
- proof method: API concurrency tests plus frontend conflict-state test
- expected evidence: ordered operation batch, `409` current-stage payload, preserved local operations, deterministic ID/path validation errors, unchanged fingerprint after rejected batch, and final explicit mutation

### Acceptance Criterion: Asynchronous Processing and Retry

- setup or precondition: upload, baseline regeneration, derivation, and retry each enter processing state; transient network, retryable LLM failure, and worker process exit are injected
- action: observe polling, expire one processing lease, restart application/reconciler, hide and restore page, then retry failed stage
- expected result: client honors `poll_after_ms`; expired claim becomes `candidate_profile_processing_abandoned`; polling stops outside processing states; last valid draft survives; retry creates new claim for recorded owning stage
- failure condition: client simulates status, duplicate worker publishes result, expired processing remains stuck, polling continues after terminal state, or approved upstream snapshot is lost
- proof method: API lifecycle/reconciler tests plus fake-clock frontend test and Playwright retry flow
- expected evidence: bounded poll sequence, expired-lease reconciliation, new claim ID on retry, preserved draft/fingerprints, and correct resumed stage

### Acceptance Criterion: Source and Regeneration Binding

- setup or precondition: baseline/derived drafts include source-block annotations and mixed regenerable/non-regenerable fields
- action: open Source, View Source, regenerate all, and regenerate one allowed and one forbidden target
- expected result: Source resolves exact block, View Source returns original retained bytes, all regeneration touches only server-declared targets, and forbidden target remains unchanged with stable error
- failure condition: UI substitutes excerpt, dereferences local path, shows wand without capability, or regeneration overwrites factual field
- proof method: API authorization/integrity tests plus browser dialog/download/regeneration flow
- expected evidence: matching block/document IDs and checksums, target-scoped mutation, and `candidate_profile_field_not_regenerable`

### Acceptance Criterion: Confirmation, Details, and Run Selection Reconcile

- setup or precondition: one attempt is confirmation-ready and one confirmed profile is later archived/restored
- action: load confirmation, confirm, open returned details, refresh Candidate Profiles, open Run picker, archive, and restore
- expected result: confirmation and details `profile.canonical` are canonical-JSON equal with same checksum; no optimistic row is created; Run picker includes profile only while server capability allows use
- failure condition: details reconstruct different data, draft appears as profile, archived profile remains selectable, or lifecycle mutation changes canonical checksum
- proof method: backend contract/store tests plus Playwright confirmation-to-Run flow
- expected evidence: equality assertion, one revision row, server-refreshed list row, and capability-driven Run options

### Acceptance Criterion: Candidate Profile LLM Settings Integration

- setup or precondition: shared Settings has valid, missing, and updated routes for both Candidate Profile tasks
- action: process ambiguous baseline, derive claims, change Settings, and retry a failed task
- expected result: existing settings API owns both routes, each actual call records resolved shared runtime evidence, deterministic/user data persists through route failure, and retry may use new route with new snapshot fingerprint
- failure condition: Candidate Profile adds provider-specific settings/client, route change mutates approved snapshot, or missing route discards draft
- proof method: settings/runtime integration tests plus UI error-action test
- expected evidence: two shared route parts, runtime evidence records, preserved draft, and new reviewed fingerprint after retry

### Acceptance Criterion: Complete Accessible Workspace Flow

- setup or precondition: supported MD, DOCX, and YAML fixtures include multiple parent/evidence/claim entries and long content
- action: complete upload through confirmation using keyboard at normal and narrow/200%-zoom layouts in supported themes
- expected result: pending/disabled/error states are announced, Source dialogs restore focus, action groups reflow, long content remains readable, and final details match confirmation
- failure condition: keyboard trap, clipped field name/value, hidden footer action, color-only status, duplicate submit, console error, or layout shift blocks task
- proof method: Playwright accessibility/responsive flow plus Chrome DevTools console/network/layout evidence
- expected evidence: completed flows for all formats, focus trace, screenshots, request log, zero console errors, and no blocking layout shift

### Acceptance Criterion: Education Uses Shared Path

- setup or precondition: profile contains thesis, academic project, seminar, and course evidence but no work experience
- action: run CV analysis against a matching entry-level job
- expected result: all education evidence is scored by the shared relevance function and eligible for global selection
- failure condition: education-only profile yields empty evidence or requires a fresh-graduate branch
- proof method: focused evidence-projection and selection regression test
- expected evidence: selected education evidence IDs and no section-specific collector call

### Acceptance Criterion: Section Symmetry

- setup or precondition: two evidence items have equal normalized text, linked skills, and context but different source sections and kinds
- action: score both items
- expected result: base relevance scores are equal and tie ordering uses evidence ID
- failure condition: section or kind changes score or reserves selection capacity
- proof method: deterministic unit test
- expected evidence: equal scores and stable order

### Acceptance Criterion: Reference Integrity

- setup or precondition: canonical profile includes multiple source documents, evidence items, and derived skills
- action: validate and resolve every reference chain
- expected result: every supported skill reaches one or more evidence items and every evidence item reaches at least one uploaded verified source; declared sources may remain additional metadata-only links
- failure condition: dangling, cross-type, duplicate, ambiguous, or declared-only evidence chain passes validation
- proof method: validator tests covering valid and invalid graphs
- expected evidence: stable validation errors and complete resolved chains

### Acceptance Criterion: Canonical YAML Self-Provenance

- setup or precondition: one valid user-authored v2 YAML omits provenance and another supplies valid earlier source metadata/refs
- action: upload both profiles
- expected result: importer records original YAML as verified uploaded source, injects uploaded document-only ref into every evidence-bearing parent/evidence statement, and preserves supplied earlier sources as declared metadata
- failure condition: user must calculate uploaded checksum, any evidence chain lacks uploaded ref, declared source gains download/verification capability, or valid declared refs are overwritten
- proof method: upload-boundary persistence test
- expected evidence: original-byte checksum, uploaded/declared origins, preserved declared refs, mandatory injected uploaded refs, and metadata-only declared-source response

### Acceptance Criterion: V1 Compatibility

- setup or precondition: current public template and representative existing v1 profiles
- action: load through compatibility adapter and run evidence projection
- expected result: work, project, achievement, and newly usable education evidence project through one v2-equivalent path; old parent refs expand deterministically
- failure condition: current valid profile becomes unusable or historical revision is rewritten
- proof method: golden compatibility tests against immutable v1 fixtures
- expected evidence: deterministic generated IDs, resolved refs, and unchanged stored v1 bytes

### Acceptance Criterion: SQLite Migration Preserves Legacy Truth

- setup or precondition: version-4 database contains succeeded active/archived profiles, null Profile Name, failed direct uploads, immutable revisions, and Runs referencing profile/revision IDs
- action: migrate to next schema version, reopen database, and attempt forced failure before version advance
- expected result: succeeded IDs/revisions/Run FKs and lifecycle remain unchanged; Profile Name fallback is persisted once; failed rows become diagnostics-only non-retryable attempts without invented bytes; failed migration rolls back to readable version `4`
- failure condition: historical JSON/checksum/ID changes, Run FK breaks, failed row remains selectable, source bytes are invented, or partial new schema survives rollback
- proof method: SQLite migration fixture test with count/checksum/FK assertions and injected transactional failure
- expected evidence: preserved row identities and checksums, clean `foreign_key_check`, deterministic legacy attempt mapping, and unchanged v4 database after injected failure

### Acceptance Criterion: Private Source Retention

- setup or precondition: one inactive unconfirmed attempt reaches 30-day purge deadline, one confirmed profile is archived, and one declared-only source exists
- action: run retention reconciliation and request source bytes/blocks for each case
- expected result: inactive attempt private content is atomically purged with safe diagnostics retained and `410`; confirmed archived profile source remains available; declared source exposes metadata only
- failure condition: abandoned private content remains, partial purge leaves extracted text, archive removes historical traceability, or declared source returns bytes
- proof method: store/reconciler retention tests plus source API capability test
- expected evidence: purge timestamps, absent private rows/artifact, retained confirmed source checksum, and correct source capabilities/status codes

### Acceptance Criterion: No Silent Partial Profile

- setup or precondition: unsupported/oversized coarse-reject source plus accepted malformed source, parser timeout, or profile with invalid references
- action: submit each upload and poll accepted attempts
- expected result: coarse reject creates no attempt; accepted-source failure remains failed and inspectable with last valid draft when applicable; no active usable revision exists
- failure condition: coarse reject creates ghost attempt, partial facts become selectable, or accepted failure discards original upload metadata
- proof method: upload-attempt failure tests
- expected evidence: stable pre-attempt `4xx`, absent attempt for coarse reject, safe failed-attempt diagnostics/checksum for accepted source, and absent active revision

### Acceptance Criterion: Runtime Projection Is Not SSOT

- setup or precondition: valid immutable v2 revision is used by repeated Runs
- action: project and select evidence more than once
- expected result: profile revision remains unchanged; projection fingerprint and payload remain stable for unchanged policy
- failure condition: runtime score/rank mutates profile or repeated projection drifts
- proof method: immutability and deterministic-fingerprint test
- expected evidence: unchanged revision checksum and identical projection fingerprints

## Completion Criteria

Specification is complete when:

1. Markdown, DOCX, and YAML coarse rejection, accepted-upload persistence, safety, and deterministic extraction/mapping are explicit
2. Step 1 upload, Step 2 baseline review, Step 3 derived review, and Step 4 confirmation use one authoritative attempt lifecycle and one attempt CAS revision
3. LLM assistance uses shared structured runtime and cannot bypass deterministic IDs, evidence references, or user review
4. upstream-edit invalidation and idempotent confirmation prevent stale or duplicate canonical revisions
5. `candidate-profile.v2` clearly separates source documents, baseline facts, derived claims, search intent, and runtime projection
6. YAML self-provenance and Markdown/DOCX provenance use one tagged `source_refs` contract, distinguish uploaded from declared sources, and always reach verified uploaded bytes
7. all admissible evidence-bearing sections use one nested evidence shape and one projector
8. skills reference evidence-item IDs and runtime derives inverse skill links without duplicated ownership
9. one section-neutral relevance and global selection contract replaces source-specific weights and quotas
10. v1 compatibility, mixed-version operation, atomic v4 migration, rollback, and non-destructive legacy grandfathering are explicit
11. failure behavior prevents silent partial profiles and unsafe provenance dereference
12. every required outcome maps to observable acceptance evidence
13. API operations, ID-addressed mutation grammar, persistence grains, stable errors, and guarded transitions have one canonical contract
14. every creation, review, source, confirmation, details, lifecycle, and Run-picker action maps to one API operation and server capability
15. executable field metadata ownership, async polling, processing lease recovery, scoped idempotency, draft batching, stale reconciliation, and deep-link behavior are explicit
16. Candidate Profile LLM routing reuses existing Settings and shared runtime without duplicate provider configuration
17. confirmation, Candidate Details, Candidate Profiles, and Run selection reconcile from same confirmed resource/checksum
18. UI Intent references canonical contracts without copying transport schemas or lifecycle rules
19. private source retention, purge, backup ownership, and post-purge API behavior are explicit
20. no unresolved behavior remains hidden as implementation detail
