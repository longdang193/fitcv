# `mycvs_v1` Markdown Schema

This file is normative for the new CV renderer. `mycvs_v1` means UTF-8 text with LF line endings, no trailing whitespace, empty YAML front matter, and deterministic checksum metadata. The checksum is SHA-256 over the normalized Markdown payload before the checksum line is appended; the checksum line itself is not included in its own input.

## Required structure

The document SHALL begin with empty YAML front matter:

```markdown
---
---
```

The document SHALL contain a candidate header and Summary. Optional sections SHALL appear in this order when their source-driven presence rule includes them:

1. `# Candidate Name`
2. contact/iconify metadata lines, when available
3. `## Summary`
4. `## Education`, when canonical education records exist
5. `## Experience`, when canonical employment records exist
6. `## Projects`, when eligible canonical project records exist
7. `## Certificates`, when one or more canonical certification records exist
8. `## Skills`, when canonical grounded skills or languages exist

The visible section order is authoritative and matches the maintained candidate CV format. The semantic Certifications section uses the wire heading `## Certificates` for compatibility.

The renderer SHALL preserve the candidate's canonical display name and SHALL emit contact metadata with the `tabler:mail`, `tabler:phone`, `tabler:brand-linkedin`, `tabler:brand-github`, and `ic:outline-location-on` Iconify identifiers when those values are present and validated.

`mycvs_v1` is a renderer/output strategy, not a replacement for the existing `cv.preset`. The configuration owner is `config/policy/cv.yaml`. The strategy consumes the canonical intermediate CV composition plan and SHALL preserve the ranking handoff identity defined by `ranking_cv_handoff_v1`.

## Composition rules

The canonical candidate profile is the factual source of truth. Selected job evidence MAY tailor relevance, wording, and support for job-specific claims, but SHALL NOT erase a valid canonical profile fact merely because the fact was not selected as requirement evidence.

The composition plan SHALL distinguish at least:

- `baseline_profile_records`
- `selected_job_support`
- `supported_job_claims`
- `unsupported_or_unknown_requirements`
- `section_policy`
- `section_priority`
- `section_budget`
- `records_selected_for_render`
- `claims_selected_for_render`
- `audit_metadata`

`approved_claims` SHALL NOT function as a global allowlist for visible CV content. Section priority and budgets SHALL come from explicit policy rather than selection state alone.

The resolved composition plan SHALL also carry `section_priority` and `section_budget`. Those fields MAY order eligible records or trim optional descriptive details, but SHALL NOT remove an eligible canonical record or mandatory identity field. Existing canonical certification records SHALL always make `## Certificates` present; no policy or evidence-selection state may suppress them.

## Required content rules

- `Summary` SHALL be present, non-empty, grounded, and approximately two to four sentences.
- Education, Experience, Projects, Certificates, and Skills SHALL be rendered when their source-driven presence rules are satisfied.
- A genuinely empty optional section SHALL be omitted rather than rendered with a placeholder. A non-empty canonical source section SHALL not be treated as empty because selected job evidence or `approved_claims` is empty.
- Experience entries SHALL preserve canonical role, employer, location, and dates when present. Each entry SHOULD contain one overview and three to five grounded achievements when enough content exists.
- Project entries SHALL preserve validated links and SHOULD contain one overview and two to four grounded achievements when enough content exists.
- Certification entries SHALL preserve canonical name, issuer, issue date, and validated URL when available. No certification may be fabricated to satisfy a count.
- Skills SHALL start from canonical grounded skills and languages, normalize aliases and duplicates, and SHALL NOT include a job-only skill without profile or attributable evidence support.
- Each structured record SHALL use Pandoc definition-list syntax: a title line, then its populated mandatory metadata row slots in the maintained order, then any populated optional metadata rows. A complete Education, Experience, Project, or Certificate record with both metadata values SHALL have exactly two consecutive `  :` rows before optional prose or achievement bullets; missing optional values SHALL omit their row rather than emit a placeholder. Experience and Project achievement bullets, when present, follow the metadata rows as ordinary Markdown list items.
- No generated text may assert a qualification that is not supported by the canonical profile or an attributable source.

## Recruiter-facing and audit content

Visible recruiter-facing content SHALL NOT contain:

- `Not provided`, `N/A`, `Unknown`, `None provided`, or equivalent placeholders;
- evidence IDs, requirement IDs, fingerprints, support states, or internal provenance metadata;
- unsupported job requirements presented as candidate facts.

The document SHALL contain exactly one hidden audit block before the checksum marker:

```text
<!-- mycvs_v1:audit {"...canonical compact JSON..."} -->
```

The audit object SHALL include job ID, profile revision, score status, confirmed gaps/unknowns, selected support identifiers, stable source identifiers, claim-level provenance, and the ranking handoff identity. Its object keys SHALL be lexicographically sorted, separators SHALL be compact, arrays SHALL use contract order, and strings SHALL use JSON escaping plus deterministic HTML-comment-safe escaping for `&`, `<`, `>`, and `--`. The audit block SHALL remain outside visible section content and SHALL not change the visible section grammar.

Project, certificate, contact, and audit links SHALL use links only when validated by the existing URL policy. Links SHALL use standard Markdown link syntax and SHALL not contain unescaped line breaks.

## Metadata and validation

The renderer SHALL append exactly one checksum marker after the audit block:

```text
<!-- mycvs_v1: schema=mycvs_v1; content_sha256=<64 lowercase hex>; handoff=<stable fingerprint> -->
```

`content_sha256` SHALL be SHA-256 over the normalized UTF-8 bytes of the complete Markdown payload from the opening `---` through the closing audit comment and one final LF, excluding the checksum marker. Normalization SHALL convert line endings to LF, preserve empty YAML front matter, remove no meaningful content, and reject trailing whitespace before hashing. Byte-for-byte fixtures SHALL cover audit serialization with zero selected support and non-empty selected support.

Validation SHALL reject:

- missing or duplicate required headings;
- invalid section order;
- non-empty YAML front matter when the contract requires empty front matter;
- visible placeholders or internal provenance identifiers;
- invalid definition-list rows;
- invalid or unsupported links;
- invalid or missing audit data;
- checksum mismatch;
- non-LF line endings or trailing whitespace;
- missing handoff identity;
- unsupported factual claims;
- missing canonical sections when their source records exist;
- a missing claim-level source/support reference after adjustment or repair;
- omission of canonical records or mandatory identity fields to satisfy a content budget or one-page constraint.

Validation SHALL allow genuinely empty optional sections to be omitted. Valid and invalid fixtures SHALL cover mixed selected evidence, zero approved claims, partial requirement support, selected-only Skills, suppressed Certifications, placeholder/provenance leakage, byte-for-byte audit/checksum output with zero selected support, claim provenance after repair, exact definition-list row grammar, optional section omission, canonical-record retention under page pressure, and one-page rendering before the new converter path is enabled.

The Markdown payload is the converter input. Converter provenance and render proof are artifact-envelope fields, not substitutes for this schema. An external adapter SHALL record the converter commit, stylesheet/template revision, input checksum, and the registered render-proof identity `mycvs_external_render_v1` (`render_status`, one-page `page_count`, `page_fit_status`, `artifact_checksum`, `content_sha256`, `template_sha256`, and `render_config_fingerprint`) before the PDF is submission-eligible. When an authoritative reference PDF is configured, the render envelope SHALL additionally record `reference_pdf_path`, `reference_pdf_sha256`, `reference_layout_status`, `reference_layout_errors`, and stable comparison metrics; a non-passing reference-layout status SHALL block PDF acceptance.
