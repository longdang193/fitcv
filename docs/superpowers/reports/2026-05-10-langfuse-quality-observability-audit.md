# Langfuse Observability Audit Report

## Scope

Audit recent Langfuse traces/sessions for FitCV stages, with focus on whether observability supports **quality review** (human-readable input/output) vs only **ops telemetry**.

- Environment: `fitcv-local-project`
- URL: `http://localhost:3000/project/fitcv-local-project/traces`
- Sampled traces:
  - `4053680fc8b8faa7f35e47065419ebb9` (`enrich`)
  - `8e3a98dce3782f639deda381ecf9fb50` (`cv_analysis`)
  - `d01bc2b870c759c86ae82b8694448ae4` (`cv_generation`)

## Executive Summary

Current instrumentation remains **ops-observability heavy** and **quality-observability light** across key stages (`enrich`, `cv_analysis`, `cv_generation`, `acceptance_review`).  
Primary issue: stage traces often show control metadata but lack reviewer-readable output payloads (`output` frequently `undefined`).

## Stage-by-Stage Findings

### 1) Enrich

**Observed**
- Input dominated by control/config fields (`config_path`, `jobs_path`, `run_mode`, `next_stage`, `run_id`).
- Output not reviewer-readable; often `undefined`/empty in trace preview.

**Impact**
- Cannot inspect semantic enrichment quality directly in Langfuse.
- Hard to evaluate whether extracted attributes improved candidate/job understanding.

### 2) CV Analysis

**Observed**
- Telemetry emphasizes run orchestration and provenance metadata.
- Missing concise human-readable analysis summary in top-level IO view.

**Impact**
- Reviewers cannot quickly answer: “Why fit/no-fit?” without diving into non-ideal metadata fields or external artifacts.

### 3) CV Generation

**Observed**
- Spans exist (`pipeline.cv_generation`, `pipeline.cv_generation_item`, `pipeline.acceptance_review_item`).
- Output frequently `undefined` at primary trace surface.
- Generated artifact quality (content preview, validator outcome summary) not visible first-class in IO.

**Impact**
- Quality evaluation loop blocked: no fast read of generated output + validation rationale in trace.

### 4) Acceptance Review

**Observed**
- Technical span naming present, but verdict/rationale not consistently surfaced as human-readable payload at top-level preview.

**Impact**
- HITL acceptance decisions are hard to audit quickly from trace alone.

## Top Problems (Ranked)

1. **Missing human-readable outputs** (`output` undefined/empty on quality stages).
2. **Ops/control metadata dominates stage payloads**.
3. **Quality signals not first-class** (buried or absent).
4. **Reviewer decision context not clearly rendered** in acceptance stage.
5. **Trace UX mismatch**: easy to inspect system state, hard to inspect model/result quality.

## Root-Cause Pattern

Instrumentation appears optimized for:
- execution control,
- stage routing/state,
- provenance and diagnostics,

but not optimized for:
- semantic quality review,
- quick human audit of input/output intent/result,
- evaluable per-item stage outcomes.

## Recommended Remediation

### Priority 1 — Mandatory readable IO contract per quality stage

For each item stage (`enrich_item`, `cv_analysis_item`, `cv_generation_item`, `acceptance_review_item`), always emit:

- **Readable input**: short bounded excerpt of relevant job/candidate/attempt context
- **Readable output**: stage-specific semantic result summary (never undefined)

### Priority 2 — Split payload domains

- Keep ops fields under `metadata.ops.*`
- Keep quality/evaluation fields in top-level readable `input`/`output` + `metadata.quality.*`

### Priority 3 — Stage-specific quality summary blocks

- `enrich`: extracted entities/deltas (skills/title/location normalization)
- `cv_analysis`: fit label, top reasons, confidence/evidence bullets
- `cv_generation`: cv preview snippet, validation summary, selected attempt id
- `acceptance_review`: action, reason, warning/violation summary, reviewer note excerpt

## Proposed Success Criteria (for next patch)

1. No quality stage with `output` undefined in sampled traces.
2. Each sampled stage trace shows readable bounded `input` and `output`.
3. Reviewer can determine outcome quality in under 15 seconds per item from trace UI.
4. Ops metadata remains available but no longer crowds primary quality view.

## Closure Statement

Audit confirms concern: current Langfuse traces are still mostly **Ops observability**, not strong **Quality observability** for `enrich` / `cv_analysis` / `cv_generation` / `acceptance_review`.  
A focused telemetry contract patch is warranted.
