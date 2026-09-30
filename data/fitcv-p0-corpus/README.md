# FitCV P0 Corpus

Public corpus snapshot for P0-A, P0-B, and P0-C work.

## Contents

- `p0a/`: source-backed DE/EN job retrieval corpus and admission report.
- `p0b/`: sanitized candidate evidence projection and two-agent-adjudicated requirement/evidence labels.
- `p0c/`: deterministic qualifier and requirement-support benchmark fixture.

## Status

- P0-A: canonical v4 fixture with 104 rows across DE/EN profiles; 84 calibration rows and 20 held-out rows. Quality and latency gates retain the incumbent.
- P0-B: canonical source-backed v2 fixture with 170 reviewed requirements; 17 supported, 152 unknown, and 1 unsupported. Benchmark-only sample; promotion remains blocked by coverage.
- P0-C: deterministic requirement-support regression fixture; not production evidence. Qualifier behavior remains covered by `tests/test_evidence.py`.
- P0-A held-out labels are published for reproducible benchmarking; do not tune against held-out results and treat them as non-independent after reuse.

## Publication boundary

- This directory is approved for public publication.
- Candidate profile YAML and original CV files are not copied here; P0-B projection contains CV-derived rows only.
- P0-B evidence text may retain organization, school, project, or location re-identifiers; direct personal identifiers are redacted, and downstream entity-level review remains required before wider reuse.
- P0-B relevance labels are separate from support verdicts: approved seed labels do not promote the support taxonomy or establish production-grade coverage.
- Versioned review packets and superseded benchmark fixtures are not part of this public snapshot; use only canonical fixture and manifest paths.
- P0-B reviewed rows embed raw evidence text; `provenance.evidence.source_file` records source provenance only and is not required to exist in this public snapshot.
- Translation pairing remains unasserted.

## Provenance

Artifacts were copied from source-admission outputs and the tracked P0-C fixture on September 27, 2026. Re-run source admission checks before using this corpus for promotion.
