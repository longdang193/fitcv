# Spec Delta

## Purpose

Defines grounded, section-specific CV analysis and deterministic `mycvs_v1` generation for final ranked jobs. The canonical candidate profile remains the factual source of truth; selected job evidence supports relevance and job-specific claims without becoming a global content allowlist.

## ADDED Requirements

### Requirement: CV composition uses canonical profile and selected evidence

The system SHALL compose recruiter-facing CV content from the canonical candidate profile, attributable source evidence, job-specific requirements, and the ranking handoff. Selected job evidence MAY tailor wording, relevance, and support for a job claim, but SHALL NOT erase a valid canonical profile fact.

#### Scenario: Canonical facts survive partial evidence selection
- **WHEN** selected evidence covers a project but does not cover the candidate's employment or certifications
- **THEN** the generated CV SHALL still use the canonical employment and certification records when those records exist, while using the selected evidence only for supported job-specific claims.

#### Scenario: Approved claims are not a global content allowlist
- **WHEN** `approved_claims` contains only a subset of profile-backed records
- **THEN** the generator SHALL NOT treat the subset as permission to delete unselected canonical education, experience, project, certification, language, or skill records.

### Requirement: CV provenance is hidden and unsupported requirements stay gaps

The system SHALL keep evidence IDs, requirement IDs, fingerprints, support states, review metadata, and other provenance in hidden audit metadata. Unsupported job requirements SHALL remain gaps and SHALL NOT become candidate claims.

#### Scenario: Unsupported requirement remains a gap
- **WHEN** a job requirement has no attributable support or the candidate lacks the required qualification
- **THEN** the analysis SHALL retain the requirement as unknown, unsupported, or a review gap and SHALL NOT add it to the visible CV as a candidate claim.

### Requirement: Header and contact content comes only from the canonical profile

The Header SHALL render the canonical candidate name and only contact fields that are present and validated by the existing profile and URL policies. Missing optional contact fields SHALL be omitted rather than replaced with placeholders. Header formatting SHALL use the maintained `mycvs_v1` Iconify/contact grammar.

#### Scenario: Missing optional contact data
- **WHEN** a canonical profile lacks an optional phone, location, LinkedIn, or GitHub value
- **THEN** the serializer SHALL omit that contact item and SHALL NOT invent or placeholder it.

### Requirement: Summary is mandatory and grounded

The Summary SHALL be non-empty and contain approximately two to four concise, grounded sentences tailored to the target job. It MAY synthesize multiple canonical profile facts and selected supported evidence, but SHALL NOT claim unsupported seniority, years of experience, certifications, technologies, industries, or responsibilities.

#### Scenario: Summary uses supported job language
- **WHEN** the profile and selected evidence support relevant job terminology
- **THEN** the Summary SHALL use that terminology only in a way that remains attributable to the profile or evidence.

#### Scenario: Summary lacks sufficient grounded content
- **WHEN** the generator cannot produce a non-empty grounded Summary
- **THEN** generation SHALL fail validation or enter the configured review-required state with a specific diagnostic and SHALL NOT emit filler or a placeholder.

### Requirement: Education preserves canonical records

Education SHALL use canonical education records as its source of truth and SHALL preserve each available degree, institution, location, and date. The section SHALL use Pandoc definition-list rows. Relevant courses, GPA, thesis, specialization, and similar optional details MAY be included only when grounded and supported by the configured content policy. Education SHALL NOT disappear because no education evidence was selected.

#### Scenario: Education has canonical records but no selected education evidence
- **WHEN** canonical education records exist and the job evidence selection contains no education item
- **THEN** the CV SHALL retain the canonical education records in definition-list format.

#### Scenario: Optional education detail is absent
- **WHEN** a canonical record lacks GPA, location, or relevant subjects
- **THEN** the serializer SHALL omit that optional detail without inventing or placeholdering it.

### Requirement: Experience preserves canonical employment and uses supported tailoring

Experience SHALL use canonical employment records as its source of truth and SHALL preserve the role, employer, location, and dates when present. Each rendered role SHALL contain one concise overview and three to five achievement-oriented bullets when enough grounded content exists. Selected evidence MAY influence supported wording and explicit relevance, but SHALL NOT determine whether a canonical employment record exists or may be rendered.

#### Scenario: No experience evidence is selected
- **WHEN** canonical employment records exist but no experience evidence is selected for the job
- **THEN** the generator SHALL retain the canonical employment records and SHALL NOT set `Experience` to an empty list solely because evidence selection is empty.

#### Scenario: Experience lacks enough grounded achievements
- **WHEN** a canonical role exists but fewer than three grounded achievements are available
- **THEN** the generator SHALL render the available truthful content, record the completeness concern for validation or review, and SHALL NOT fabricate achievements to reach the target count.

### Requirement: Projects use canonical records with explicit relevance policy

Projects SHALL use eligible canonical project records and preserve validated project links. The configured project-composition policy MAY order or allocate content using job relevance, but selected evidence SHALL NOT erase a canonical project merely because it was not selected as requirement evidence. Each rendered project SHOULD contain one overview and two to four achievement-oriented bullets when sufficient grounded content exists.

#### Scenario: Relevant project is selected
- **WHEN** a canonical project has selected support for a target job
- **THEN** the generator MAY apply the configured relevance ordering or content budget to that project, while preserving other eligible canonical projects as required by the same policy.

#### Scenario: Project link is invalid
- **WHEN** a project URL fails the existing URL validation policy
- **THEN** the serializer SHALL omit the invalid link or fail the configured validation gate and SHALL NOT emit an unvalidated URL.

### Requirement: Certifications use canonical records independently

Certifications SHALL use canonical certification records independently of selected job evidence. When records exist, the CV SHALL preserve the name, issuer, issue date, and validated URL when available.

The generator SHALL NOT fabricate a certification, and an optional focus line SHALL use only grounded certification metadata. The `mycvs_v1` wire heading remains `## Certificates` for compatibility.

#### Scenario: Certifications are suppressed by empty selection
- **WHEN** canonical certifications exist but the selected certification evidence list is empty
- **THEN** the generator SHALL still render the canonical certification records and SHALL NOT remove the section solely because selected evidence is empty.

#### Scenario: Candidate has no certifications
- **WHEN** the canonical profile contains no certification records
- **THEN** the generator SHALL omit the Certificates section rather than emit `Not provided` or an invented credential.

#### Scenario: Certification presence is not policy-controlled
- **WHEN** the canonical profile contains one or more certification records after normalization
- **THEN** the generator SHALL emit `## Certificates`; selected evidence, `approved_claims`, section budget, and relevance policy SHALL NOT suppress the records or mark the section absent.

### Requirement: Skills start from canonical grounded skills

Skills SHALL start from canonical grounded skills, normalize aliases and duplicates through the canonical skill resolver, and group them using the configured skill taxonomy. Job requirements MAY influence relevance ordering or an explicit content budget. Lack of selected requirement evidence SHALL NOT automatically remove a canonical skill. A skill appearing only in the job description SHALL NOT enter the CV without profile or attributable evidence support.

#### Scenario: Selected evidence contains only one skill
- **WHEN** selected evidence supports one skill but the canonical profile contains additional grounded skills and languages
- **THEN** the generator SHALL retain the additional grounded skills and languages according to the configured taxonomy and content budget.

#### Scenario: Job-only skill is unsupported
- **WHEN** a skill appears in the job description but not in the canonical profile or attributable evidence
- **THEN** the generator SHALL keep it as an unsupported requirement or gap and SHALL NOT render it as a candidate skill.

### Requirement: Section presence is evaluated independently

The generator SHALL evaluate each section from its canonical source records and section policy, not from global evidence selection. Header and Summary are mandatory; Education, Experience, Projects, and Skills are present when their canonical source records exist; Certificates is present whenever canonical certification records exist. A section policy MAY order records or select optional descriptive details, but MAY NOT change these source-driven presence decisions.

#### Scenario: Optional section has no canonical records
- **WHEN** an optional section has no usable canonical records
- **THEN** the serializer SHALL omit the section and SHALL NOT emit a placeholder heading or placeholder text.

### Requirement: CV composition plan separates sources and claims

Before initial creation, the generator SHALL produce a provenance-preserving composition plan with all fields defined by the `mycvs_v1` schema.

#### Scenario: Plan preserves provenance
- **WHEN** a plan is created from selected evidence
- **THEN** it SHALL contain `baseline_profile_records`, `selected_job_support`, `supported_job_claims`, `unsupported_or_unknown_requirements`, `section_policy`, `section_priority`, `section_budget`, `records_selected_for_render`, `claims_selected_for_render`, and `audit_metadata`, and each rendered claim SHALL retain machine-checkable references to canonical source records and/or attributable support identifiers.

#### Scenario: Resolved plan is reused
- **WHEN** initial creation, bounded adjustment, repair, serialization, or final validation runs
- **THEN** the same resolved policy snapshot and provenance-preserving plan SHALL be used rather than rebuilding an evidence-only allowlist.

### Requirement: CV composition plan controls all generation passes

`section_priority` and `section_budget` SHALL come from explicit configuration or policy, never solely from selected evidence. They MAY affect ordering and optional descriptive detail, but SHALL NOT remove eligible canonical records or mandatory identity fields. The plan SHALL be the single input for creation, adjustment, repair, serialization, and final validation.

#### Scenario: Adjustment preserves the composition contract
- **WHEN** a bounded adjustment pass runs
- **THEN** it SHALL preserve canonical records, provenance, and unsupported-requirement gaps.

### Requirement: `mycvs_v1` Markdown follows the maintained schema

The serializer SHALL emit UTF-8 Markdown with LF line endings, empty YAML front matter, the maintained section order, Pandoc `  :` rows, hidden audit metadata, and the checksum rules in `schemas/mycvs_v1.md`.

#### Scenario: Schema grammar is preserved
- **WHEN** a rendered record has definition-list metadata
- **THEN** the serializer SHALL emit the maintained title-plus-definition-row grammar.

### Requirement: Recruiter-facing CV content is clean

Visible recruiter-facing content SHALL NOT contain `Not provided`, `N/A`, `Unknown`, `None provided`, equivalent placeholder tokens, evidence IDs, requirement IDs, fingerprints, or internal provenance fields. The audit block SHALL remain outside visible section content.

#### Scenario: Placeholder or provenance leakage is detected
- **WHEN** visible Markdown contains a placeholder token or internal evidence/provenance identifier
- **THEN** Markdown validation SHALL fail before PDF conversion and SHALL persist an actionable diagnostic.

#### Scenario: Definition-list grammar is valid
- **WHEN** Education, Experience, Projects, or Certificates contains a rendered record
- **THEN** the serializer SHALL emit the record title followed by each populated mandatory metadata row in the maintained order (the full record has two definition rows when both metadata values exist), followed by optional populated rows and achievement bullets only where that section permits them; it SHALL omit missing optional values rather than emit empty or placeholder rows.

### Requirement: Final validation enforces composition invariants

Before PDF acceptance, validation SHALL enforce the composition invariants and source-driven section-presence rules.

#### Scenario: Unsupported requirement is rejected
- **WHEN** an unsupported requirement appears in candidate content
- **THEN** validation SHALL fail before PDF acceptance.

#### Scenario: Canonical records and claims remain valid
- **WHEN** final validation runs
- **THEN** it SHALL confirm a grounded Summary, canonical sections when source records exist, omission of empty optional sections, clean visible content, valid claim-level support, and retention of all eligible canonical records and mandatory identity fields.

#### Scenario: Certification policy cannot suppress canonical records
- **WHEN** canonical certifications exist and the selected certification evidence is empty or a relevance policy excludes certifications
- **THEN** the generator SHALL still emit `## Certificates` with the canonical records, and validation SHALL reject any plan that marks the section absent.

#### Scenario: Repaired claims retain provenance
- **WHEN** bounded adjustment or repair rewrites a Summary sentence or achievement bullet
- **THEN** the rewritten claim SHALL retain valid source references, or validation SHALL fail or enter the configured review-required state before PDF acceptance.

#### Scenario: Required canonical content does not fit
- **WHEN** all eligible canonical records and mandatory identity fields cannot fit the one-page/page-fit contract after optional detail reduction
- **THEN** generation SHALL fail or enter the configured review-required state with a page-fit diagnostic and SHALL NOT omit canonical records silently.

### Requirement: Final validation enforces renderer and page-fit gates

The configured strategy SHALL use the bundled `mycvs_v1` renderer. The final PDF SHALL pass the existing render proof and one-page/page-fit gate before PDF status becomes accepted.

#### Scenario: Mixed-evidence regression passes
- **WHEN** one project claim is selected while canonical employment, certifications, skills, and education are present
- **THEN** the final CV SHALL retain those canonical sections and SHALL contain no placeholder text or visible evidence IDs.

#### Scenario: Zero-approved-claims regression passes
- **WHEN** no approved job claims exist but the canonical profile contains usable records
- **THEN** the generator SHALL produce a factual baseline CV instead of an empty or placeholder-filled document.

#### Scenario: Partial-support regression remains truthful
- **WHEN** a candidate has a related project or skill but not the exact JD qualification
- **THEN** the related fact MAY appear when grounded, the missing qualification SHALL remain a gap, and the CV SHALL NOT assert the unsupported qualification.

#### Scenario: One-page PDF rendering succeeds
- **WHEN** Markdown validation passes and the bundled renderer produces a PDF
- **THEN** PDF status SHALL become generated only after the PDF is one page, passes page-fit/render proof, and has matching artifact integrity metadata.

### Requirement: CV adjustment and lifecycle outcomes remain bounded and independent

The system SHALL retain the existing bounded adjustment loop and independent generation, review, PDF, and submission-clearance outcomes. A review-required result MAY persist valid Markdown and attempt PDF generation, but submission SHALL remain blocked until review approval. Converter failure SHALL remain a technical failure and SHALL NOT rewrite a valid Markdown artifact as a generic generation success.

#### Scenario: Review-required output remains grounded
- **WHEN** factual or critical concerns remain after the bounded adjustment budget
- **THEN** the system SHALL persist the grounded artifacts and review diagnostics, preserve any valid PDF independently, and keep submission clearance blocked.
