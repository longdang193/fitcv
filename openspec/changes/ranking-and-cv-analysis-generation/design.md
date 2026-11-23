# Design

## Context

Stage 7 receives an immutable ranking-to-CV handoff, the canonical candidate profile, attributable evidence, and the target job requirements. The existing pipeline already owns stage checkpoints, evidence projections, CV analysis/generation, Markdown serialization, PDF conversion, render proof, and persisted lifecycle outcomes.

The current CV composition contract is too coarse: selected job evidence can act as a global content allowlist, certifications can be suppressed when their selected-evidence list is empty, Skills can be restricted to selected evidence, Experience can become empty when no experience evidence is selected, and the serializer can turn missing content into `Not provided.`. The design below makes composition section-specific while preserving the existing ranking, shortlist, persistence, and PDF boundaries.

## Goals / Non-Goals

**Goals:**

- Compose every new CV from the complete canonical candidate profile plus selected job evidence.
- Give each section its own source of truth, tailoring behavior, minimum content, section-presence rule, and validation invariants.
- Separate canonical facts from selected job support, supported claims, unsupported requirements, rendered records, and hidden audit metadata.
- Remove visible placeholders and visible evidence/provenance identifiers.
- Preserve the maintained `mycvs_v1` Markdown grammar, empty YAML front matter, Pandoc definition-list rows, deterministic audit metadata, checksum scope, bundled renderer, and one-page/page-fit acceptance.
- Keep bounded adjustment, review-required persistence, PDF status, and submission-clearance behavior independent and compatible.

**Non-Goals:**

- Changing ranking order, AI-score calculation, score validity, Pareto-front admission/promotion, shortlist generation, or ranking-to-CV handoff semantics.
- Rewriting profile ingestion, evidence projection, or downstream fit truth.
- Deleting or backfilling historic personalized ranking or legacy CV artifacts.
- Introducing a new model provider, database, service, or workflow engine.
- Automatically prioritizing a profile record solely because one of its evidence IDs was selected. Any ordering or page-budget behavior must come from explicit section policy.

## Implementation Boundaries

- Ranking remains owned by `src/fitcv/ranking.py` and `src/fitcv/ranking_contract.py`. The shortlist capability remains the owner of Pareto admission and promotion.
- The immutable ranking-to-CV handoff remains produced and persisted by the existing ranking-stage artifact boundary. CV stages consume it; they do not reconstruct mutable ranking context or re-rank jobs.
- CV analysis and generation remain owned by `src/fitcv/agentic_cv_analysis.py`, `src/fitcv/agentic_cv_generation.py`, and the worker boundary.
- The intermediate CV model, serializer, Markdown validator, and renderer adapter remain owned by `src/fitcv/cv_generator.py` and the existing render-proof/artifact-contract modules.
- `config/policy/cv.yaml` remains the configuration owner for renderer strategy, section policy, section ordering, and content budgets.
- Existing lifecycle and persistence boundaries remain responsible for independent generation, review, PDF, and submission-clearance outcomes.

## Composition Model

The pipeline SHALL build one provenance-preserving composition plan before serialization:

```text
canonical candidate profile
        +
selected job support and supported claims
        +
unsupported/unknown job requirements
        +
explicit section policies
        ↓
CV composition plan
        ↓
mycvs_v1 Markdown serializer and validator
        ↓
bundled myCVs renderer
        ↓
one-page/page-fit/render-proof acceptance
```

The plan SHALL contain at least:

```text
baseline_profile_records
selected_job_support
supported_job_claims
unsupported_or_unknown_requirements
section_policy
section_priority
section_budget
records_selected_for_render
claims_selected_for_render
audit_metadata
```

`baseline_profile_records` are the candidate facts that may be rendered. `selected_job_support` identifies evidence selected for this job. `supported_job_claims` are job-specific assertions that pass the evidence policy. `unsupported_or_unknown_requirements` are retained for analysis/review and cannot become candidate claims. `records_selected_for_render` and `claims_selected_for_render` are the output of section policies, not a copy of `approved_claims`. `audit_metadata` retains provenance without leaking it into visible Markdown.

Each `claims_selected_for_render` item SHALL include a stable claim key, visible text, section, and machine-checkable references to one or more canonical record IDs and/or attributable support IDs. The plan SHALL be constructed before initial creation and SHALL carry the resolved section-policy snapshot through bounded adjustment, repair, serialization, and final validation. A repair path SHALL use the same plan rather than rebuilding an evidence-only allowlist.

## Implementation Sequence and Ownership

Implementation SHALL proceed in this order so that the serializer never becomes the place where factual eligibility is decided:

1. **Normalize inputs and build the plan.** `src/fitcv/agentic_cv_generation.py::build_cv_content_plan` SHALL receive the canonical profile, analysis/handoff support, and resolved CV configuration, then produce the complete plan. `src/fitcv/cv_generator.py::project_authorized_profile` and `_build_generation_prompt_context` SHALL stop treating selected evidence as a profile-record filter for the new `mycvs_v1` path. The plan builder, not the prompt formatter, owns canonical-record eligibility.
2. **Resolve section policy.** `src/fitcv/section_policy.py`, `src/fitcv/cv_presets.py`, `src/fitcv/config.py`, and `config/policy/cv.yaml` SHALL define and validate section enablement, explicit `section_priority`, optional `section_budget`, and the per-section source/tailoring/minimum/presence rules. Certification eligibility SHALL be profile-driven and SHALL not depend on selected certification evidence.
3. **Generate against the plan.** The initial generation path in `src/fitcv/agentic_cv_generation.py::generate_from_analysis` and its fresh-generation helper SHALL pass the same plan to prompt construction. Adjustment and repair paths (`merge_repaired_section`, `_determine_repair_targets`, and their callers) SHALL update visible text only when the resulting claims still satisfy the plan's provenance references; they SHALL not create a new evidence-only plan.
4. **Serialize and validate.** `src/fitcv/cv_generator.py::serialize_mycvs_v1` SHALL render only `records_selected_for_render` and `claims_selected_for_render`, omit empty optional sections, and write the hidden audit/checksum block. `validate_mycvs_v1_markdown` SHALL reject placeholders, visible provenance, invalid definition-list rows, missing canonical records, missing claim references, and checksum/audit mismatches before conversion.
5. **Render and accept.** The existing renderer adapter and render-proof/artifact-contract boundary SHALL consume the validated Markdown unchanged. The bundled renderer SHALL be used for the active `mycvs_v1` path; one-page/page-fit failure SHALL remain observable and SHALL never be repaired by dropping canonical records.

The implementation SHALL keep these ownership boundaries explicit: ranking and shortlist code only supplies the immutable handoff; CV composition owns section policy and content selection; the serializer owns wire grammar; the validator owns contract rejection; the renderer owns PDF evidence; persistence owns independent lifecycle statuses.

## Concrete Data Flow

The implementation SHOULD keep the current dictionary-based boundary where practical, but the following keys are mandatory and must be present at each handoff:

| Boundary | Required input | Required output / invariant |
| --- | --- | --- |
| Analysis → plan | canonical profile, job snapshot, selected support, supported claims, gaps/unknowns, ranking handoff | complete composition plan with policy snapshot and stable provenance references |
| Plan → generation | complete composition plan | prompt context may emphasize selected support but cannot remove canonical records |
| Generation → repair/adjustment | plan plus candidate structured CV | repaired sections retain claim keys and source references; no evidence-only re-projection |
| Structured CV → Markdown | plan plus structured content | only eligible records/claims serialize; optional empty sections are omitted |
| Markdown → validator | Markdown plus plan/audit | visible content is provenance-free and checksum/audit are deterministic |
| Validator → renderer | validated Markdown | renderer receives no unvalidated or placeholder-bearing payload |
| Renderer → lifecycle | render proof and artifact checksums | PDF becomes generated only after one-page/page-fit and identity checks pass |

The plan must be persisted in the generation trace/result envelope when that envelope already exists, but audit metadata must remain the only provenance representation inside recruiter-facing Markdown. No new persistence table or service is required.

## Section Policies

Each section has an independent policy with four mandatory parts: source of truth, tailoring behavior, minimum content, and validation rule.

| Section | Source of truth | Tailoring behavior | Minimum/presence | Validation |
| --- | --- | --- | --- | --- |
| Header/contact | Canonical profile only | None beyond configured display formatting | Candidate name required; optional contact fields omitted when absent | No invented fields; validated links; maintained Iconify grammar |
| Summary | Canonical profile plus supported job context | Use grounded JD terminology and positioning | Mandatory, approximately 2–4 sentences | Non-empty, grounded, no unsupported seniority/qualification claims |
| Education | Canonical education records | Optional grounded details may be selected by explicit policy | Present when canonical records exist | Preserve degree, institution, location, dates; definition-list syntax |
| Experience | Canonical employment records | Selected evidence may influence supported wording and explicit relevance policy, not record existence | Present when employment exists; one overview and 3–5 bullets when enough content exists | Preserve role/employer/location/dates; no fabricated achievements |
| Projects | Eligible canonical project records | Explicit job-relevance policy may order records and select optional detail, but may not omit an eligible record | Present when eligible projects exist; one overview and 2–4 bullets when enough content exists | Validated links; no unsupported project claims |
| Certifications (`Certificates` wire heading) | Canonical certification records | Optional grounded focus/relevance line only | Present whenever one or more canonical certification records exist; omitted only when none exist | Preserve name/issuer/date/validated URL; no fabricated credentials |
| Skills | Canonical grounded skills and languages | Normalize/deduplicate and apply explicit JD relevance policy | Present when grounded skills or languages exist | No job-only skills; proficiency only when supported |

The absence of selected evidence does not remove a canonical record. Canonical eligibility is deterministic: a non-tombstoned profile record is eligible when it has the section's required identity field(s) after canonical normalization; selected evidence is never an eligibility predicate. `section_priority` MAY order eligible records, and `section_budget` MAY reduce optional descriptions or bullets, but neither may remove a canonical record or mandatory identity field. If optional detail reduction still cannot satisfy the one-page/page-fit contract, validation SHALL fail or enter review rather than silently dropping records. Any ordering or content budget must be explicit in the resolved `section_policy`; it cannot be inferred solely from selection state.

## Serialization and Audit Separation

`mycvs_v1` is a recruiter-facing output format. The serializer SHALL emit:

- UTF-8 text with LF line endings and no trailing whitespace;
- empty YAML front matter;
- the maintained section order among sections that are present;
- Pandoc `  :` definition-list rows for structured records;
- validated links only;
- exactly one deterministic hidden audit block after the visible content and before the checksum marker;
- the schema/checksum metadata required by `schemas/mycvs_v1.md`.

Visible content SHALL exclude `Not provided`, `N/A`, `Unknown`, `None provided`, equivalent placeholders, evidence IDs, requirement IDs, fingerprints, support states, and internal provenance. The audit block MAY contain those identifiers and SHALL remain outside visible section content.

The wire heading remains `## Certificates` for compatibility with the maintained template, even though the semantic section is Certifications. Optional sections are source-driven: a section with no eligible canonical records is omitted rather than rendered with a placeholder heading or placeholder text. Existing canonical certifications cannot be omitted by policy.

The audit block SHALL contain one compact canonical JSON object between `<!-- mycvs_v1:audit ` and ` -->`. Object keys SHALL be lexicographically sorted, separators SHALL be compact, arrays SHALL use the contract order, and strings SHALL use JSON escaping plus HTML-comment-safe escaping for `&`, `<`, `>`, and `--`. The audit object SHALL include job identity, profile revision, score status, gaps/unknowns, selected support IDs, stable source IDs, claim-level provenance, and the ranking handoff identity. The checksum marker SHALL be the only content after the audit block. `content_sha256` SHALL hash the normalized UTF-8 bytes of the complete Markdown payload from the opening front matter through the closing audit comment and one final LF, excluding the checksum marker itself. This makes audit content part of the checksum input while keeping it outside recruiter-facing content.

## Validation and PDF Acceptance

Before conversion, the Markdown validator SHALL check grounded content, section presence, placeholder/provenance leakage, definition-list grammar, section order, empty front matter, link validity, audit metadata, handoff identity, and checksum integrity.

The configured `mycvs_v1` strategy SHALL use the bundled myCVs renderer. PDF status becomes generated only after the existing artifact-integrity, render-proof, and one-page/page-fit checks pass. A valid Markdown artifact may be retained when PDF conversion fails. Review-required output may retain a valid PDF, but submission remains blocked until review approval.

## Compatibility and Migration

Historic ranking and CV artifacts remain readable with their original metadata and contracts. The new composition contract applies only to new `mycvs_v1` writes and does not rewrite existing Europass or legacy artifacts. Existing configuration defaults and safe paths remain unchanged until the renderer release gate is satisfied.

## Decisions

1. **Canonical profile is the factual baseline.** Evidence selection changes support and permitted job-specific claims, not whether a canonical fact exists.
2. **Section policies are explicit.** Each section owns its own source, tailoring, minimum content, presence, and validation behavior.
3. **No global `approved_claims` allowlist.** The composition plan preserves independent profile records and evidence-backed claims.
4. **No visible placeholders or provenance.** Missing optional data is omitted; factual or structural deficiencies fail validation or enter review with a specific diagnostic.
5. **Renderer grammar remains stable.** Empty YAML front matter and Pandoc definition-list syntax are part of the `mycvs_v1` contract. The existing `Certificates` heading is retained for wire compatibility.
6. **Page fit does not justify silent data loss.** If the explicit section policy cannot fit the one-page contract, the result fails or enters the configured review path rather than deleting facts merely because they were not selected as evidence.
7. **Ranking ownership is unchanged.** Ranking, AI scoring, Pareto-front admission, shortlist promotion, and the ranking-to-CV handoff remain outside this refinement.
8. **Plan before prompt.** The composition plan is built before any LLM prompt so generation cannot redefine eligibility. A prompt-only fix was rejected because it would leave serializer, repair, and adjustment paths inconsistent.
9. **Validator before renderer.** Placeholder/provenance and canonical-retention checks run before PDF conversion. A renderer-only check was rejected because invalid Markdown could still be persisted or rendered by alternate paths.
10. **Reuse existing policy/config seams.** Section policy is added to the existing `section_policy.py`, preset, and CV configuration seams rather than introducing a parallel policy registry. This preserves one source of truth and keeps rollback to the existing renderer strategy possible.

## Risks / Trade-offs

- **[Policy drift]** Section-specific policies are more explicit than a single allowlist → keep the policy matrix in `section_policy.py`/config and cover every row with focused tests.
- **[Canonical record loss]** Existing projection or repair callers may still filter by evidence → make the plan the only eligibility input for `mycvs_v1` and add mixed/zero-support regression fixtures.
- **[Page pressure]** Preserving canonical facts can increase one-page failures → reduce only optional detail through explicit budgets, then fail or enter review with diagnostics; never drop records silently.
- **[Wire compatibility]** Existing consumers may expect legacy headings → retain `## Certificates` and test historic artifact reads before enabling the new path.
- **[Converter drift]** A successful Markdown build is not sufficient evidence of a valid one-page PDF → require the existing render-proof identity, checksum, and page-fit gate.

## Open Questions

None for this planning revision. The semantic Certifications section uses the existing `Certificates` wire heading for compatibility.
