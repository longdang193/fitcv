---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: canonical-candidate-uniform-evidence-projection
targets:
  - data/candidate_profile.v2.sample.yaml
  - data/candidate_profile.template.yaml
  - src/fitcv/candidate.py
  - src/fitcv/evidence.py
  - src/fitcv_cp/sqlite_store.py
  - tests/test_candidate.py
  - tests/test_candidate_profile_template_contract.py
  - docs/configuration.md
  - docs/pipeline.md
related_features:
  - cv_system
related_stages:
  - cv-analysis
  - cv-generation
---

# Canonical Candidate Profile and Uniform Evidence Projection

## Goal and Problem

### Problem

- current behavior or opportunity: Candidate Profile input is a hand-authored YAML contract. Its evidence collector projects work experience, projects, and achievements through separate paths, while education is accepted by profile reference validation but excluded from evidence retrieval and scoring.
- affected users, systems, or maintainers: non-technical candidates uploading CVs, fresh graduates whose strongest evidence is academic, Candidate Profile ingestion, CV analysis, CV generation, and maintainers changing evidence-bearing profile sections.
- evidence:
  - `src/fitcv/candidate.py` requires the v1 `experiences`, `skills`, `projects`, `achievements`, and `preferences` sections and validates references against parent record IDs.
  - `src/fitcv/evidence.py` collects only experience, project, and achievement entries and assigns section-specific types, weights, quotas, and trimming behavior.
  - `tests/test_candidate.py` proves education IDs may satisfy `skills[].evidence_refs`, but no corresponding education item enters runtime evidence retrieval.
  - `src/fitcv_cp/sqlite_store.py` accepts only UTF-8 `.yaml` Candidate Profile uploads and passes them directly to the v1 loader.
- consequence of no change: semantically equivalent evidence receives different treatment based on where it appears, academic evidence cannot compete uniformly with work evidence, uploaded CVs cannot become pipeline-ready profiles without manual restructuring, and derived claims cannot always be traced to exact source material.

### Goal

- desired outcome: every admissible CV or canonical-profile upload produces one validated `CanonicalCandidateProfile`; every evidence-bearing statement projects through one deterministic `CandidateEvidenceItem` contract; every derived claim remains traceable to evidence and original upload provenance.
- observable success:
  - equivalent statements from experience, education, projects, achievements, certifications, or volunteering enter the same relevance and selection path
  - fresh graduates require no pipeline special case
  - canonical YAML, JSON, PDF, DOCX, and plain-text inputs become indistinguishable after canonicalization
  - derived claim traceability follows `claim -> evidence_refs -> evidence item -> source_refs -> source document`
  - canonical facts remain SSOT; runtime projection is derived and never becomes a second editable profile

## Required Outcomes

### Outcome: One Canonical Profile

- affected actor or system: Candidate Profile ingestion and persistence
- required result: each successful upload produces one immutable, validated `candidate-profile.v2` revision independent of source format
- success condition: downstream stages consume only the canonical revision and never branch on PDF, DOCX, text, YAML, or JSON origin

### Outcome: Uniform Evidence Projection

- affected actor or system: CV analysis evidence retrieval and selection
- required result: every nested canonical evidence statement becomes one `candidate-evidence.v1` item through the same projector
- success condition: source section and evidence kind are provenance metadata, not separate collector implementations or scoring bonuses

### Outcome: Complete Traceability

- affected actor or system: users, diagnostics, generated CV claims, and audit surfaces
- required result: every projected evidence item resolves to at least one source document, and every derived skill claim resolves to at least one evidence item unless explicitly marked unsupported
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
| Is education already considered valid support? | Education parent IDs pass current dangling-reference validation. | `tests/test_candidate.py` | high | Education support extends existing reference intent rather than introducing a separate subsystem. |

### Scope

- included behavior:
  - `candidate-profile.v2` identity, provenance, baseline facts, derived claims, and validation
  - ingestion from PDF, DOCX, UTF-8 plain text, YAML, and JSON
  - canonical-YAML self-provenance behavior
  - one runtime `candidate-evidence.v1` projection
  - uniform relevance, ordering, and selection semantics
  - v1 compatibility adaptation and mixed-version runtime behavior
  - failure diagnostics required to prevent silent data loss
- affected boundaries:
  - upload validation and source retention
  - source-format parser or canonical-profile importer
  - Candidate Profile revision persistence
  - profile validation and reference integrity
  - CV analysis evidence projection and selection
  - generated-CV evidence traceability
- admissible cases:
  - experienced candidate with only work evidence
  - fresh graduate with only education evidence
  - candidate with work, education, portfolio projects, achievements, certifications, or volunteering in any combination
  - user-authored canonical YAML or JSON
  - parser-created canonical profile from supported CV document formats
  - empty optional sections and a profile with no selectable evidence
- compatibility expectation: current valid v1 profiles remain runnable through one adapter; no pipeline consumer requires source-format-specific behavior.

### Non-Goals

- visual CV editor or manual profile-editing UX
- OCR for image-only PDFs
- legacy binary `.doc`, rich-text, image, or archive ingestion
- external credential verification or factual truth verification
- automatic merging of different uploaded CVs into one revision
- changing job ingestion, ranking, or user search-preference semantics
- making parser confidence a proficiency score or employment-verification score

### Requirements and Behavioral Contract

#### Requirement: Canonical Profile Layers

- trigger or actor: successful ingestion of any supported source
- preconditions: source passes upload safety checks and parser/importer can produce a structurally valid profile
- required behavior: persisted profile separates four semantic layers:
  1. source documents: immutable metadata about uploaded bytes
  2. baseline facts: candidate-authored or source-extracted profile content in natural sections
  3. derived claims: normalized skills or equivalent claims linked to evidence
  4. runtime projection: deterministic evidence items computed from canonical facts and claims
- output or state change: one immutable `candidate-profile.v2` revision plus ingestion diagnostics
- failure behavior: failed or incomplete canonicalization does not create an active usable revision; original upload metadata and safe failure diagnostics remain inspectable
- observable acceptance: no baseline fact is copied into a second editable top-level evidence store, and no runtime-only scoring field is written back as baseline truth

#### Requirement: Canonical Identity

- trigger or actor: canonical-profile importer or document parser
- preconditions: an input record, evidence statement, or derived claim is accepted
- required behavior:
  - `schema_version` is exactly `candidate-profile.v2`
  - every source document, parent record, evidence item, and derived claim has a non-empty stable `id`
  - IDs are globally unique within one profile revision
  - valid caller-supplied IDs in canonical YAML or JSON are preserved
  - parser-created IDs are deterministic for identical original bytes, parser version, source locator, and normalized extracted content
  - IDs are immutable inside a revision
- output or state change: references use IDs, never array positions, titles, names, or mutable display labels
- failure behavior: duplicate, blank, malformed, or ambiguous IDs reject canonicalization
- observable acceptance: reordering YAML arrays does not break any reference in an already-valid profile

#### Requirement: Required Canonical Surface

- trigger or actor: user-authored canonical upload or parser-created canonical profile
- preconditions: input is intended to become a Candidate Profile revision
- required behavior:
  - canonical upload requires `schema_version`, non-blank `name`, and at least one recognized evidence-bearing section
  - canonical YAML or JSON authors provide every parent, evidence, and skill `id`; importer does not invent missing semantic IDs for an allegedly canonical document
  - `source_documents` and missing `source_refs` are ingestion-owned defaults and are not required from a canonical YAML or JSON author
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
  - `skills`, `languages`, `headline`, `summary`, `interests`, contact fields, dates, URLs, locations, tags, and search preferences are optional unless another active contract requires them for a specific output
- output or state change: importer emits one normalized canonical mapping with defaults applied before validation and persistence
- failure behavior: malformed required fields reject canonicalization; a structurally valid profile with no evidence persists as an inspectable successful revision whose derived `use_for_run` capability is false with reason `no_candidate_evidence`
- observable acceptance: non-technical users do not author hashes, parser metadata, runtime scores, or source locators for canonical YAML uploads

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
  - `source_documents[]` records `id`, safe `filename`, `media_type`, SHA-256 of original bytes, and `parser.name`/`parser.version`
  - `source_refs[]` contains `document_id` plus format-appropriate locator data when a stable locator exists
  - PDF locators use one-based `page`
  - DOCX locators use one-based `paragraph`
  - text locators use one-based inclusive `line_start` and `line_end`
  - one statement spanning multiple locations uses multiple source references
  - source metadata is descriptive only; filenames, paths, URLs, or locators never authorize filesystem or network reads
- output or state change: baseline parent records and nested evidence statements retain provenance at their own fact grain
- failure behavior: unknown `document_id`, invalid locator range, or locator incompatible with declared media type rejects canonicalization
- observable acceptance: every projected evidence item resolves to original source metadata without trusting an external path

#### Requirement: Canonical YAML or JSON Upload Provenance

- trigger or actor: user uploads `candidate-profile.v2` YAML or JSON
- preconditions: uploaded document parses as a mapping and satisfies canonical field rules other than ingestion-owned provenance defaults
- required behavior:
  - importer hashes original uploaded bytes and creates one source-document record for the uploaded canonical file
  - existing valid source documents and source references are preserved
  - each parent record or evidence statement missing `source_refs` receives a reference to the uploaded canonical document
  - injected canonical-file references require only `document_id`; evidence `id` identifies the exact canonical statement
  - importer records its identity under `parser.name` and `parser.version` like every other ingestion path
- output or state change: stored canonical revision may contain added provenance metadata, while source-document checksum continues to describe original uploaded bytes
- failure behavior: supplied dangling or contradictory references are rejected rather than silently replaced
- observable acceptance: trace chain for a manually authored skill ends at the canonical YAML or JSON upload when no earlier source provenance was supplied

#### Requirement: Evidence-Bearing Parent Shape

- trigger or actor: parser/importer emits work, education, project, achievement, certification, or volunteering records
- preconditions: parent record contains a stable `id`
- required behavior:
  - each evidence-bearing parent uses the same `evidence` list
  - each evidence entry requires `id`, `kind`, non-blank `text`, and canonical `source_refs`
  - `title` and `date` are optional evidence metadata
  - `kind` is a non-empty stable snake-case value used for explanation and rendering, not scoring authority
  - parent sections retain their natural metadata such as role/company, degree/institution, project name/URL, issuer, organization, dates, location, tags, and themes
  - parent metadata is not independently selectable evidence unless represented by a nested evidence statement
- output or state change: thesis, course, seminar, academic project, responsibility, work achievement, project highlight, certification proof, and volunteer contribution share one evidence grain
- failure behavior: unsupported evidence value types or blank evidence text reject canonicalization
- observable acceptance: adding a new `kind` does not require a new collector or relevance formula

#### Requirement: Derived Skill Claims

- trigger or actor: parser, canonical importer, or approved user-authored canonical profile
- preconditions: a normalized skill claim is retained
- required behavior:
  - each `skills[]` entry contains `id`, normalized `name`, `origin`, bounded `confidence`, and ordered unique `evidence_refs`
  - `origin` distinguishes at least `extracted_explicit`, `inferred`, and `user_asserted`
  - `confidence` describes extraction or derivation confidence only
  - `evidence_refs` target nested evidence-item IDs, never parent IDs
  - supported skill claims require at least one evidence reference
  - unsupported user assertions may be retained only with explicit `support_status: unsupported`; they remain visible but cannot contribute evidence-based score or generated CV claims
- output or state change: evidence-to-skill associations have one canonical owner in `skills[].evidence_refs`
- failure behavior: dangling refs, duplicate refs, invalid confidence, or a supported claim with no refs reject canonicalization
- observable acceptance: runtime evidence derives linked skill names by reversing `skills[].evidence_refs`; evidence items do not duplicate a canonical skill list

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
end: "present"
role_family: null
domain_tags: []
responsibility_themes: []
skills:
  - "Machine learning"
  - "Statistical analysis"
source_refs:
  - document_id: "doc_cv_1"
    page: 1
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
  - identical canonical input produces identical projected IDs, fields, order, and scoring text
  - immutable Run input identifies exact Candidate Profile revision and checksum
  - persisted selected-evidence artifacts are audit/cache projections, not editable profile owners
- output or state change: retries and resumes can reproduce evidence selection inputs
- failure behavior: incompatible schema or projector version fails visibly rather than guessing a conversion
- observable acceptance: projection fingerprint remains stable across repeated runs with unchanged profile and policy

### Constraints and Alternatives

- constraint: source code and tests remain runtime authority until this proposed specification is implemented and verified
- constraint: private uploaded CV content and provenance must not enter public sample or generated public documentation
- constraint: upload boundary must retain existing filename sanitization, byte limits, safe parsing, and failed-attempt visibility
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

### Decision: Canonical Upload Is Its Own Source When Needed

- context: user-authored YAML or JSON may contain valid facts but no earlier document provenance
- selected approach: importer creates a source-document record for original canonical bytes and fills only missing source references
- rationale: traceability remains uniform without requiring non-technical users to author checksums or locators
- alternatives considered: make source refs optional; require users to provide full provenance manually
- accepted trade-offs: stored canonical bytes differ from uploaded bytes because ingestion metadata is added
- affected owners and boundaries: upload attempt owns original checksum; canonical revision owns enriched provenance

### Decision: One Section-Neutral Relevance Function

- context: current section weights and quotas make work history structurally stronger than education
- selected approach: score all `candidate-evidence.v1` items with one function and one global budget
- rationale: evidence content and linked skills determine relevance, not candidate career stage or section label
- alternatives considered: education-specific weight; career-stage switch; reserved per-section quotas
- accepted trade-offs: existing section-biased result ordering changes when equivalent education evidence is more relevant
- affected owners and boundaries: CV analysis policy owns relevance inputs and budget; profile schema owns no scoring policy

### Compatibility, Migration, and Risk

- old behavior: unversioned v1 YAML is primary input; skills may reference parent IDs; evidence collection branches by experience/project/achievement; education is not collected; uploads accept `.yaml` only
- new behavior: supported inputs canonicalize to v2; claims reference evidence IDs; all evidence-bearing sections flatten through one projector; one section-neutral selector consumes the result
- compatibility boundary: existing stored v1 revisions remain immutable and use the adapter at runtime; new uploads create v2 revisions
- migration or backfill: no eager rewrite is required; optional explicit save-as-v2 may create a new revision after user inspection
- rollout and rollback: v2 ingestion and adapter may be disabled together while existing v1 loader remains available; no historical revision is destructively rewritten
- deprecation or consumer impact: direct consumers of parent-targeting `evidence_refs`, current `source_ref` array-index strings, or section-specific evidence types must move to `candidate-evidence.v1`
- risk:
  - parser invents unsupported facts
    - mitigation: confidence, source refs, failed-attempt diagnostics, and user inspection preserve uncertainty and provenance
  - canonical YAML carries malicious paths or URLs
    - mitigation: provenance fields are inert metadata and never trigger reads
  - v1 expansion changes selection volume
    - mitigation: one global budget and deterministic relevance order bound output
  - new projector silently omits evidence
    - mitigation: acceptance compares canonical evidence count with projection count and fails on malformed items
  - private source content leaks into public fixtures
    - mitigation: public-safe sample remains synthetic and publication boundary remains enforced

## Invariants and Edge Cases

### Invariants

- one immutable Candidate Profile revision is canonical SSOT for candidate facts, provenance, derived claims, and search intent
- one nested evidence entry produces exactly one runtime evidence item
- every projected evidence ID is globally unique and resolves back to one canonical evidence entry
- every `source_refs[].document_id` resolves to one source document in the same revision
- every supported `skills[].evidence_refs[]` resolves to one nested evidence item in the same revision
- evidence items never own duplicated canonical skill lists
- runtime scoring fields never become baseline profile facts
- source section and evidence kind never alter base relevance
- canonicalization and projection are deterministic for unchanged inputs and versions
- original upload checksum always describes original bytes, not enriched canonical serialization
- search preferences never become evidence

### Edge Cases

- empty or minimal input: identity/contact-only canonical input may persist only if product policy allows an unusable profile state; it cannot start a pipeline Run until at least one valid evidence item exists
- normal and large input: projector emits one item per evidence statement and selector applies existing configured global limits; no per-section expansion limit silently drops canonical evidence before scoring
- duplicate, missing, malformed, or unsupported data: reject duplicate IDs, dangling refs, blank evidence text, invalid confidence, invalid hashes, incompatible locators, and unsupported file formats with stable failure codes
- retry, cancellation, timeout, partial failure, or concurrency: failed parsing never activates a partial revision; repeated processing of the same attempt cannot mutate a previously stored revision
- migration or mixed-version state: v1 and v2 revisions may coexist; both converge before evidence retrieval, and pipeline output records source profile schema plus effective projection schema
- generated-source consistency: parser/importer version and original checksum are recorded; all injected source refs target the canonical upload's source-document record
- security or accessibility boundary: uploaded content is data, never executable configuration; YAML uses safe loading; archive/path traversal and remote dereference are forbidden; user-facing failures identify field/location without echoing unnecessary private content

## Validation Plan

### Acceptance Criterion: All Supported Inputs Converge

- setup or precondition: equivalent candidate content exists as canonical YAML, JSON, PDF, DOCX, and text fixtures
- action: ingest each fixture
- expected result: each successful revision satisfies `candidate-profile.v2` and projects semantically equivalent evidence, claims, and provenance
- failure condition: downstream code branches on original format or equivalent facts disappear
- proof method: ingestion contract tests plus normalized projection comparison excluding source-format locator differences
- expected evidence: successful revisions, recorded checksums/parsers, and equivalent `candidate-evidence.v1` payloads

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
- expected result: every supported skill reaches one or more evidence items and every evidence item reaches one or more source documents
- failure condition: dangling, cross-type, duplicate, or ambiguous reference passes validation
- proof method: validator tests covering valid and invalid graphs
- expected evidence: stable validation errors and complete resolved chains

### Acceptance Criterion: Canonical YAML Self-Provenance

- setup or precondition: valid user-authored v2 YAML omits source documents and source refs
- action: upload profile
- expected result: importer records original YAML as source document and injects document-only refs into missing parent/evidence provenance
- failure condition: user must manually calculate checksum, refs remain missing, or existing valid refs are overwritten
- proof method: upload-boundary persistence test
- expected evidence: original-byte checksum, importer metadata, preserved supplied refs, and injected missing refs

### Acceptance Criterion: V1 Compatibility

- setup or precondition: current public template and representative existing v1 profiles
- action: load through compatibility adapter and run evidence projection
- expected result: work, project, achievement, and newly usable education evidence project through one v2-equivalent path; old parent refs expand deterministically
- failure condition: current valid profile becomes unusable or historical revision is rewritten
- proof method: golden compatibility tests against immutable v1 fixtures
- expected evidence: deterministic generated IDs, resolved refs, and unchanged stored v1 bytes

### Acceptance Criterion: No Silent Partial Profile

- setup or precondition: malformed source, unsupported source, parser timeout, or profile with invalid references
- action: create Candidate Profile attempt
- expected result: attempt remains failed and inspectable; no active usable revision exists
- failure condition: partial facts become selectable or failure discards original upload metadata
- proof method: upload-attempt failure tests
- expected evidence: stable failure code, safe message, checksum/filename metadata, and absent active revision

### Acceptance Criterion: Runtime Projection Is Not SSOT

- setup or precondition: valid immutable v2 revision is used by repeated Runs
- action: project and select evidence more than once
- expected result: profile revision remains unchanged; projection fingerprint and payload remain stable for unchanged policy
- failure condition: runtime score/rank mutates profile or repeated projection drifts
- proof method: immutability and deterministic-fingerprint test
- expected evidence: unchanged revision checksum and identical projection fingerprints

## Completion Criteria

Specification is complete when:

1. `candidate-profile.v2` clearly separates source documents, baseline facts, derived claims, search intent, and runtime projection
2. canonical YAML self-provenance and parsed-document provenance use one `source_refs` contract
3. all admissible evidence-bearing sections use one nested evidence shape and one projector
4. skills reference evidence-item IDs and runtime derives inverse skill links without duplicated ownership
5. one section-neutral relevance and global selection contract replaces source-specific weights and quotas
6. v1 compatibility, mixed-version operation, rollback, and non-destructive migration are explicit
7. failure behavior prevents silent partial profiles and unsafe provenance dereference
8. every required outcome maps to observable acceptance evidence
9. no unresolved behavior remains hidden as implementation detail
