# `mycvs_v1` Markdown Schema

This file is normative for the new CV renderer. `mycvs_v1` means UTF-8 text with LF line endings and no trailing whitespace. The checksum is SHA-256 over the normalized Markdown payload before the checksum line is appended; the checksum line itself is not included in its own input.

## Required structure

The document SHALL contain exactly these top-level headings, in this order, with one blank line between sections:

1. `# Candidate Name`
2. contact/iconify metadata lines (when available)
3. `## Summary`
4. `## Education`
5. `## Experience`
6. `## Projects`
7. `## Certificates`
8. `## Skills`

The renderer SHALL preserve the candidate's canonical display name, use only grounded profile facts, and emit contact metadata with the `tabler:mail`, `tabler:phone`, `tabler:brand-linkedin`, `tabler:brand-github`, and `ic:outline-location-on` Iconify identifiers when those values are present. The visible section order is authoritative and matches the maintained candidate CV format.

`mycvs_v1` is a renderer/output strategy, not a replacement for the existing `cv.preset`. The configuration owner is `config/policy/cv.yaml`: the existing `cv.preset: europass` and its historic artifacts remain unchanged, while an additive renderer strategy selects `mycvs_v1` for new writes. The strategy consumes the canonical intermediate CV model and SHALL preserve the ranking handoff identity defined by `ranking_cv_handoff_v1`.

## Required content rules

- `Summary`, `Education`, `Experience`, `Projects`, `Certificates`, and `Skills` SHALL be present even when a section is empty; an empty section SHALL contain `Not provided.` rather than an invented claim.
- Each experience item SHALL retain its source evidence identifiers when evidence exists.
- An HTML audit block SHALL include job ID, profile revision, score status, confirmed gaps/unknowns, and stable source identifiers; it SHALL remain outside the visible section headings.
- Project and certificate links, when present, and audit source links SHALL use links only when the source link is validated by the existing URL policy.
- Links SHALL use standard Markdown link syntax and SHALL not contain unescaped line breaks.
- No generated text may assert a qualification that is not supported by the canonical profile or an attributable source.

## Metadata and validation

The renderer SHALL append exactly one metadata block after the final section:

```text
<!-- mycvs_v1: schema=mycvs_v1; content_sha256=<64 lowercase hex>; handoff=<stable fingerprint> -->
```

Validation SHALL reject missing or duplicate headings, invalid metadata or audit data, checksum mismatch, non-LF line endings, unsupported links, missing handoff identity, and unsupported factual claims. Valid and invalid fixtures SHALL be added with the implementation task before the new converter path is enabled.

The Markdown payload is the converter input. Converter provenance and render proof are artifact-envelope fields, not substitutes for this schema: an external adapter SHALL record the converter commit, stylesheet/template revision, input checksum, and the registered render-proof identity `mycvs_external_render_v1` (`render_status`, one-page `page_count`, `page_fit_status`, `artifact_checksum`, `content_sha256`, `template_sha256`, and `render_config_fingerprint`) before the PDF is submission-eligible.
