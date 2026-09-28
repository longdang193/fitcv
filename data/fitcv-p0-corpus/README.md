# FitCV P0 Corpus

Local corpus snapshot for future P0-A, P0-B, and P0-C work.

## Contents

- `p0a/`: source-backed DE/EN job retrieval corpus and admission report.
- `p0b/`: sanitized candidate evidence projection, canonical taxonomy, review queue, independent labels, and conservative adjudication output.
- `p0c/`: deterministic qualifier and requirement-support benchmark fixture.

## Status

- P0-A: 100 jobs; 50 DE and 50 EN; 40 calibration and 10 held-out per language.
- P0-B: 60 adjudicated rows covering 52 requirement instances; 100-row review queue; 50 expanded rows independently reviewed; 4 conservative-unknown disagreements; benchmark-only; promotion remains blocked.
- P0-C: synthetic regression fixture; not production evidence.

P0-B artifacts:
- `canonical_taxonomy.json`: versioned requirement types, qualifier dimensions, and verdict vocabulary; observed labels use `supported` and `unknown`.
- `requirement_instances.jsonl`: 100 deterministic review-queue rows, stratified 50 DE/50 EN and 80/20 calibration/held-out.
- `reviewed_requirement_evidence_expanded.jsonl`: 60 adjudicated labels; one redacted candidate profile; no translation pairing asserted.
- `reviewed_requirement_evidence_expanded_manifest.json`: hashes, counts, reviewer agreement, and promotion blockers.

## Privacy boundary

- Keep this directory in the private repository only. Do not publish it to a public mirror.
- Candidate profile YAML and original CV files are not copied here.
- Corpus provenance uses repository-local redacted source aliases; original local paths are not retained.
- Direct email and phone scan passed for committed P0-B artifacts; re-identifiers remain disclosed below.
- P0-B evidence text may retain organization, school, project, or location re-identifiers.
- Translation pairing remains unasserted.

## Provenance

Artifacts were copied from ignored `tmp/p0/` outputs and the tracked P0-C fixture on September 27, 2026. Queue and adjudication artifacts were generated on September 28, 2026. Re-run source admission checks before using this corpus for promotion.
