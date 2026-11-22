# Proposal

## Why

FitCV needs a maintained contract for the post-shortlist Ranking and CV Analysis & Generation stages. The current implementation still exposes legacy personalized ranking fields and a Europass-oriented CV path, while the FigJam design requires an auditable AI-score handoff, grounded CV analysis, deterministic `myCVs` Markdown, and independent review/PDF outcomes.

## What Changes

- Define a versioned ranking-order contract whose new order uses AI compatibility as the authoritative ranking value; keep the currently active personalized order authoritative for existing checkpoints until an explicit order-version migration, and keep its fields readable throughout.
- Preserve the existing bounded ranking-input contract: mandatory job/candidate facts, validated shortlist evidence, and the 12,000-character request budget.
- Preserve explicit invalid, unscored, and retryable ranking outcomes instead of converting them to fabricated zero scores.
- Require a versioned ranking-to-CV handoff containing the job qualifiers, baseline rank/score, canonical evidence, gaps, profile revision, and provenance.
- Define CV analysis as grounded in canonical profile evidence and job-specific requirements, with a bounded adjustment loop and separate hard factual/template checks from soft ATS/recruiter quality optimization.
- Define deterministic `mycvs_v1` Markdown rendering and validation before conversion.
- Preserve the existing one-page/render acceptance gate and define the canonical `mycvs_v1` schema, fixtures, and checksum scope before enabling the converter.
- Separate CV generation status, review status, and PDF status; review-required output still attempts PDF generation, and converter failure remains a technical failure.
- Block submission while review is required, even when PDF generation succeeds.
- Preserve historical personalized ranking and CV artifacts; do not rewrite or delete them as part of migration.
- Keep Pareto admission and promotion owned by the shortlist capability; this stage consumes the admitted shortlist and does not duplicate shortlist gates.

## Capabilities

### New Capabilities

- `ai-ranking`: Authoritative AI compatibility scoring, explicit score validity, deterministic ranking handoff, and provenance.
- `cv-analysis-generation`: Grounded CV analysis, bounded correction, deterministic `mycvs_v1` rendering, review metadata, and PDF conversion outcomes.

### Modified Capabilities

None. No maintained top-level capability specs existed before this change; these are new contracts for the two stages.

## Impact

- Ranking: `src/fitcv/ranking.py`, ranking orchestration, persisted ranking artifacts, and any readers of personalized rank/residual fields.
- CV analysis/generation: `src/fitcv/agentic_cv_analysis.py`, `src/fitcv/agentic_cv_generation.py`, `src/fitcv/cv_generator.py`, `src/fitcv/cv_presets.py`, and stage/checkpoint persistence.
- Configuration: the active CV preset and external `myCVs` converter integration must be versioned and pinned before release.
- Tests and observability: add contract tests for invalid scores, provenance, handoff completeness, deterministic Markdown, independent status transitions, converter failure, and historic-artifact compatibility.
- No new service or dependency is required. The existing evidence projection, stage runner, persistence, and PDF boundary remain the implementation substrate.
