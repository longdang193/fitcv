# FitCV P0 Corpus

Local corpus snapshot for future P0-A, P0-B, and P0-C work.

## Contents

- `p0a/`: source-backed DE/EN job retrieval corpus and admission report.
- `p0b/`: sanitized candidate evidence projection and two-agent-adjudicated requirement/evidence labels.
- `p0c/`: deterministic qualifier and requirement-support benchmark fixture.

## Status

- P0-A: 100 jobs; 50 DE and 50 EN; 40 calibration and 10 held-out per language.
- P0-B: 10 reviewed requirement/evidence pairs across 3 postings; benchmark-only sample; promotion remains blocked by coverage.
- P0-C: synthetic regression fixture; not production evidence.

## Privacy boundary

- Keep this directory local/private. Do not publish or commit it without review.
- Candidate profile YAML and original CV files are not copied here.
- P0-B evidence text may retain organization, school, project, or location re-identifiers.
- Translation pairing remains unasserted.

## Provenance

Artifacts were copied from ignored `tmp/p0/` outputs and the tracked P0-C fixture on September 27, 2026. Re-run source admission checks before using this corpus for promotion.
