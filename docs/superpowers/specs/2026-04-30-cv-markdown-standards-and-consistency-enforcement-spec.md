---
layer: change
artifact_type: spec
status: proposed
parent_thread: workstream-bounded-agentic-cv-quality.agentic-cv-quality-analysis-grounding
targets:
  - src/fitcv/cv_generator.py
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv/validator.py
  - src/fitcv/pipeline.py
  - src/fitcv_cp/app.py
  - src/fitcv/prompts/templates/cv_generation_structured_write_v1.md
  - docs/observability.md
  - tests/test_cv_generator.py
  - tests/test_pipeline_agentic_late_stage.py
  - tests/test_fitcv_cp/test_app.py
related_features:
  - cv_system
  - inspection_debugging
  - trigger_run_management
related_stages:
  - cv_generation
---

# CV Markdown Standards And Consistency Enforcement

## Summary

Introduce a bounded CV markdown standards contract with deterministic post-generation normalization, stronger structural validation, and explicit observability for markdown-quality outcomes.

This keeps generated CVs consistently readable and easier to trust across providers and run modes.

## Problem

Current generated CV markdown can be semantically valid but operationally inconsistent:

- section/heading structure can drift between runs or providers
- bullet and spacing conventions are not strictly normalized
- date formatting and section density can vary significantly
- operators can see accepted generation without clear markdown-quality diagnostics

These inconsistencies reduce downstream usability even when generation technically succeeds.

## Goals

- define one canonical markdown contract for persisted CV output
- normalize markdown formatting deterministically before persistence
- enforce structural and depth-oriented quality checks
- route non-compliant outputs into existing bounded review flows
- expose markdown quality diagnostics in run artifacts

## Non-Goals

- no free-form WYSIWYG CV editing in control plane
- no replacement of structured CV generation contract
- no unbounded or style-heavy rewriting layer

## Proposed Contract

## 1) Canonical Markdown Output Standard

Persisted markdown must follow a stable skeleton:

1. `# {Candidate Name}`
2. optional one-line role/profile subtitle
3. `## Experience`
4. `## Certifications`
5. `## Projects`

Section bodies must follow canonical formatting:

- bullet marker is `- ` only
- single blank line between top-level sections
- no empty required sections
- no placeholder tokens (for example `TBD`, `Lorem ipsum`, `Candidate Name`)

## 2) Deterministic Post-Generation Normalization

Before persistence, apply a bounded normalizer that:

- normalizes heading levels and ordering to required section contract
- normalizes bullet marker style
- trims redundant whitespace and trailing blank blocks
- normalizes date ranges into one configured display style
- preserves semantic content (no hallucinated additions)

If normalization cannot preserve a required section cleanly, mark as failed/review-required through existing late-stage controls.

## 3) Markdown Quality Validation Layer

Add markdown-quality checks after structured validation:

- required headings present in canonical order
- minimum content density for `Experience` and `Projects`
- no section with heading but zero meaningful lines
- no unsupported claims markers already blocked by analysis (`do_not_claim`)

Outcome policy:

- hard structural break -> `validation_failed`
- borderline but salvageable format/depth -> `review_required`
- clean pass -> `accepted`

## 4) Prompt Contract Tightening

Update CV generation prompt template contract to explicitly require:

- canonical heading sequence
- bullet convention
- no prose outside contract sections
- grounded concise bullets with measurable outcomes when supported by evidence

Prompt tightening is a support layer, not a sole enforcement mechanism.

## 5) Observability And Operator Surfaces

Expose markdown-quality diagnostics in:

- `cv_generation` stage quality metrics
- `cv-debug.json` per-job debug records
- `hitl-review-audit.json` reason fields when markdown quality triggers review
- run detail quality surface (compact counts by markdown-quality outcome)

## Acceptance Criteria

- accepted CV markdown follows canonical structure and formatting rules
- non-compliant markdown is either rejected or flagged `review_required`
- observed markdown drift across providers is reduced and measurable
- operator can identify markdown-quality-triggered review items quickly
- artifact and run-detail surfaces remain aligned on outcome truth

## Validation

```powershell
python -m pytest tests/test_cv_generator.py -k "markdown or validate or normalize"
python -m pytest tests/test_pipeline_agentic_late_stage.py -k "review_required or validation_failed"
python -m pytest tests/test_fitcv_cp/test_app.py -k "run_detail or review or export"
python scripts/validate_repo_contracts.py --fast
```

## Risks

- over-strict formatting checks may reduce acceptance rate unnecessarily
- normalization that is too aggressive may hide genuine model quality issues
- provider-specific markdown quirks may require bounded adapter rules

## Rollout / Revert

- rollout: enable validator + normalizer with conservative thresholds first, then tighten using observed outcomes
- revert: disable markdown-quality gating while keeping structured validation and existing acceptance path intact

## Next Artifact

Implementation execution map with waves:

1. canonical contract + prompt alignment
2. deterministic normalizer
3. markdown-quality validator + status routing
4. observability and operator surface integration
