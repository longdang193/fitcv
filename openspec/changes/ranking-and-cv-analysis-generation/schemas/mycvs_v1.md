# `mycvs_v1` Markdown Schema

This file is normative for the new CV renderer. `mycvs_v1` means UTF-8 text with LF line endings and no trailing whitespace. The checksum is SHA-256 over the normalized Markdown payload before the checksum line is appended; the checksum line itself is not included in its own input.

## Required structure

The document SHALL contain exactly these top-level headings, in this order, with one blank line between sections:

1. `# Candidate Name`
2. `## Summary`
3. `## Skills`
4. `## Experience`
5. `## Education`
6. `## Evidence and Fit Notes`
7. `## Sources`

The renderer SHALL preserve the candidate's canonical display name, use only grounded profile facts, and keep job-specific fit notes separate from canonical experience claims.

## Required content rules

- `Summary`, `Skills`, `Experience`, and `Education` SHALL be present even when a section is empty; an empty section SHALL contain `Not provided.` rather than an invented claim.
- Each experience item SHALL retain its source evidence identifiers when evidence exists.
- `Evidence and Fit Notes` SHALL include job ID, ranking handoff fingerprint, profile revision, score status, and confirmed gaps/unknowns.
- `Sources` SHALL contain stable source identifiers and links only when the source link is validated by the existing URL policy.
- Links SHALL use standard Markdown link syntax and SHALL not contain unescaped line breaks.
- No generated text may assert a qualification that is not supported by the canonical profile or an attributable source.

## Metadata and validation

The renderer SHALL append exactly one metadata block after the final section:

```text
<!-- mycvs_v1: schema=mycvs_v1; content_sha256=<64 lowercase hex>; handoff=<stable fingerprint> -->
```

Validation SHALL reject missing or duplicate headings, invalid metadata, checksum mismatch, non-LF line endings, unsupported links, missing handoff identity, and unsupported factual claims. Valid and invalid fixtures SHALL be added with the implementation task before the new converter path is enabled.
