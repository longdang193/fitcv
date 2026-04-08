---
feature_type: modify
feature_name: cv_system
status: draft
summary: "Align retrieval, ranking, fit classification, validation, and debug surfaces so the pipeline has one clear decision contract per stage."
invariants:
  - "Each pipeline stage must have one clear responsibility and one explicit output contract."
  - "A later stage must not silently reinterpret an earlier stage's decision without explicit policy."
  - "Run export and debug artifacts must reflect the real runtime decision path."
  - "Cleanup should reduce hidden duplication before introducing new scoring logic."
  - "The pipeline must remain grounded in persisted job and candidate data."
---

# Pipeline Decision Consistency Cleanup Design

## Affected Feature Contracts

- [`docs/features/cv_system/cv_system.yaml`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/cv_system/cv_system.yaml)
- [`docs/features/trigger_run_management/trigger_run_management.yaml`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/trigger_run_management/trigger_run_management.yaml)
- [`docs/features/inspection_debugging/inspection_debugging.yaml`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/inspection_debugging/inspection_debugging.yaml)

## Triage

Feature type: MODIFY  
Summary: Align ranking, fit, retrieval, validation, and debug signals so the pipeline makes consistent decisions and explains them clearly.  
Reasoning: This is not a new product capability. The current system already performs retrieval, reranking, gap analysis, CV generation, validation, and debugging, but several of those layers overlap or contradict each other in ways that make behavior hard to trust and hard to debug.  
Invariants:
- Raw retrieval, AI scoring, ranking, gap analysis, validation, and CV generation must each have one clear responsibility.
- Later stages must not silently override earlier stages without an explicit policy.
- Debug and export surfaces must expose the actual runtime path rather than reconstructed guesses.
- Cleanup should simplify reasoning first, not add more parallel scoring systems.
- Existing run export and CV debug artifacts must remain supported during rollout.
Dependencies:
- `cv_system`
- `trigger_run_management`
- `inspection_debugging`
- ranking, retrieval, validation, and CV-generation runtime seams
Affected docs:
  feature_yaml:
    - `docs/features/cv_system/cv_system.yaml`
    - `docs/features/trigger_run_management/trigger_run_management.yaml`
    - `docs/features/inspection_debugging/inspection_debugging.yaml`
  feature_history:
    - `docs/features/cv_system/history.md`
    - `docs/features/trigger_run_management/history.md`
    - `docs/features/inspection_debugging/history.md`
  feature_docs:
    - none
  cross_cutting_docs:
    - none
  readme: none
  generated:
    - `docs/generated/*`
Generated refresh required: yes  
Spec needed: yes  
Plan needed: yes  
Risk level: high

## Why We Came Up With This Spec

This spec came from debugging real runs where the pipeline technically succeeded but its decision story was hard to trust.

The most important observed contradictions were:

- in [`logs/fitcv-run-db508a62-45d0-4a51-8a17-9f8da88130c4-results.json`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-db508a62-45d0-4a51-8a17-9f8da88130c4-results.json), one ranked job shows:
  - `scores.fit_label = "skip"`
  - `cv.fit_classification = "strong"`
- the same run shows:
  - `shortlisted_jobs_total = 1`
  - `scoring_shortlisted_jobs_total = 2`
  - which is valid after shortlist backfill, but hard to interpret without understanding the stage split
- structured CV artifacts can still carry empty or weak section content while markdown validation reports success

During code inspection, several mismatches appeared between the intended architecture and the runtime behavior:

- the ranking config declares a six-feature ranking model, but runtime ranking currently uses only the features that happen to already be present
- AI scoring and gap analysis both produce fit labels
- AI reranking is documented as evidence-grounded, but the pipeline does not currently populate reranker evidence
- validation is markdown-first, even though generation is now structured-first

So the core problem is not a single bug. It is that the pipeline currently contains several overlapping or partially disconnected decision systems.

## Problem Statement

The pipeline currently has hidden redundancy and stage-to-stage contradictions in six areas:

1. ranking feature computation versus ranking configuration
2. AI fit classification versus gap-based fit classification
3. documented evidence-grounded reranking versus actual reranker inputs
4. gap-analysis field expectations versus the enriched job contract
5. structured-first CV generation versus split section-validation ownership
6. config naming and reader ownership for shared ranking/retrieval settings

This causes three classes of failure:

- runtime decisions that are internally inconsistent
- exports and debug artifacts that are confusing even when technically correct
- configuration and documentation that overstate what the pipeline is actually doing

## Current Contradictions

### 1. Ranking feature model is only partially implemented

[`config/ranking.yaml`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/config/ranking.yaml) defines a weighted model using:

- `ai_score`
- `must_have_match`
- `vector_similarity`
- `title_relevance`
- `seniority_fit`
- `preference_fit`

But [`build_ranking_features()`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/pipeline.py:469) currently:

- merges shortlist rows and AI-score rows
- carries through whatever fields are already present
- computes `final_score`
- does not compute the deterministic ranking helpers from [`ranking.py`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/ranking.py)

That means the configured ranking architecture and the runtime ranking behavior are not actually the same system.

### 2. Ranking and CV generation both classify fit independently

The pipeline currently has two fit systems:

- AI reranking fit:
  - derived in [`ai_score.py`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/ai_score.py)
  - carried forward as `fit_label`
- gap-based fit:
  - derived in [`gap_analysis.py`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/gap_analysis.py)
  - re-evaluated in Layer 4 inside [`pipeline.py`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/pipeline.py)

The recent `_resolve_layer4_fit(...)` change reduces the worst silent downgrade behavior, but it does not remove the architectural overlap. The pipeline still lets two different subsystems describe the same job’s fit in different ways.

### 3. AI reranking is described as evidence-grounded, but runtime does not ground it

[`ai_score.py`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/ai_score.py) explicitly supports `top_evidence` and includes it in the reranking prompt.

But the runtime shortlist path:

- does not retrieve evidence before AI scoring
- does not populate `top_evidence`
- therefore typically sends empty evidence lists into the reranker

So the reranker is less grounded than the module contract suggests.

### 4. Gap analysis depends on field contracts that upstream does not clearly own

[`pipeline.py`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/pipeline.py) still passes `years_required` into [`compute_gap()`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/gap_analysis.py), but the enriched job contract produced by [`enrich.py`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/enrich.py) clearly owns:

- `years_experience_min`
- `years_experience_max`

That means one stage is still depending on a years signal that upstream does not present as a stable part of the enriched-job contract.

This is a decision-consistency problem because:

- gap analysis appears to support years-based fit risk
- but runtime field ownership for that signal is ambiguous
- so the stage contract is harder to trust than the function signature suggests

### 5. Gap analysis declares an overclaim-evidence path that runtime does not activate

[`compute_gap()`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/gap_analysis.py) supports `candidate_evidence` and uses it for leadership-style overclaim checks.

But the Layer 4 pipeline call does not currently supply `candidate_evidence`.

So the current system is in a half-state:

- the module contract implies evidence-aware overclaim detection
- the runtime path usually evaluates gap risk without the evidence input needed for that branch

That should be resolved explicitly:

- either gap analysis becomes truly evidence-aware in runtime
- or the dormant overclaim path is removed from the active contract for now

### 6. Structured-first generation and markdown validation are not fully aligned

CV generation now produces structured output first, then renders markdown.

But [`validator.py`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/validator.py) still validates:

- markdown section presence
- employer/project grounding in markdown text
- skills-section provenance in markdown text

That is useful, but it leaves a blind spot:

- structured artifacts can be semantically weak or empty in places
- validation only fails if the markdown surface violates the current section rules

This is especially visible when an enabled section such as Summary is structurally present but semantically empty.

There is also a more concrete ownership split inside the current implementation:

- [`cv_generator.py`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/cv_generator.py) hardcodes a required structured-section set
- [`validator.py`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/validator.py) derives required markdown sections from config composition

So the structured artifact and the rendered artifact are not yet governed by one clearly shared section contract.

### 7. Config naming is partially inconsistent with runtime readers

[`config/ranking.yaml`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/config/ranking.yaml) defines `missing_value_defaults`.

But [`build_ranking_features()`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/pipeline.py:510) reads `ranking_null_defaults`.

That means runtime does not cleanly consume the documented configuration contract.

There is a similar split in retrieval sizing:

- [`pipeline.py`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/pipeline.py) reads `pipeline.vector_search_top_n`
- [`vector_search.py`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/vector_search.py) still defaults from `vector_top_n`

Those two keys currently happen to align in config, but they still create two runtime readers for the same concept.

## What Is Intentional, Not a Problem

Some overlap in the pipeline is legitimate and should be preserved:

- rule filters are deterministic policy gates before retrieval
- vector retrieval is a recall-oriented shortlist stage, not a final quality judgment
- AI reranking is a semantic ranking stage
- gap analysis is still useful for:
  - grounded CV emphasis
  - overclaim protection
  - debug explainability
- validation is still needed after generation even when upstream fit and evidence are strong

So the cleanup goal is not “only one stage may judge anything.” The goal is “each stage judges one thing clearly, and downstream stages do not duplicate upstream decisions without an explicit contract.”

## Design Goal

Refactor the pipeline so that:

- each stage has one clear decision responsibility
- ranking-time fit authority and CV-generation eligibility use one explicit decision contract after deterministic rule filters
- debug/export surfaces expose stage-local decisions without mixing semantics
- configuration, docs, and runtime behavior describe the same system

## Core Design Principle

The pipeline should distinguish clearly between:

- **selection**
  - which jobs survive to the next stage
- **scoring**
  - numeric signals used for ordering
- **fit classification**
  - human-readable category for a job
- **grounding/debug explanation**
  - why a job looks like a fit or risk
- **validation**
  - whether the generated artifact is acceptable

Each of those should have a primary owner.

Visibility does not imply authority:

- a stage output may remain visible in exports/debug
- without becoming authoritative for downstream decisions

To avoid ambiguity, the cleanup should distinguish between:

- **ranking fit label**
  - the authoritative fit label used for ranking/CV eligibility
- **gap explanation / risk summary**
  - explanatory grounded signals that may remain visible without owning the decision

## Phase 1 Scope

The first rollout should be a **Phase 1 consistency cleanup**, not a full platform-wide refactor.

Phase 1 should focus on:

- aligning ranking config with the features actually computed at runtime
- choosing one primary post-filter fit authority for ranking and CV eligibility
- correcting reranker contract/docs to match actual runtime grounding
- aligning shared config keys with the runtime readers that use them
- making export/debug surfaces expose the true stage decision chain

Phase 1 should not try to fully redesign:

- rich evidence-grounded reranking
- broad semantic-content scoring in validation
- a new deterministic ranking model
- a full gap-analysis redesign beyond input/authority cleanup

## Recommended Target Architecture

### Stage 1: Rule filtering remains the only deterministic pre-retrieval gate

Keep:

- pre-enrichment global filters
- candidate-specific rule filters

Responsibility:

- reject obviously out-of-policy jobs

Not responsible for:

- final fit labels
- ranking
- CV gating after ranking

### Stage 2: Retrieval remains a recall stage

Keep vector retrieval focused on:

- semantic candidate-to-job recall
- shortlist ordering by similarity

Responsibility:

- produce raw retrieval hits

Not responsible for:

- final fit labels
- final CV eligibility

If a scoring shortlist backfill exists, it should remain visible as a retrieval/debug distinction, not be confused with ranking.

### Stage 3: AI reranking becomes the primary ranking fit authority

Recommended rule:

- `ai_score` and `fit_label` from reranking are the primary post-filter fit signal
- after deterministic rule filtering, reranker fit is the default authority for:
  - ranking-time fit labeling
  - CV-generation eligibility
- except for separately documented deterministic gates such as:
  - explicit rule-filter rejection
  - explicit artifact-validation rejection after generation

This means:

- ranking/export should present one primary fit label from the reranker
- later stages may add explanation or safeguards, but not silently introduce a second competing fit taxonomy

### Stage 4: Gap analysis becomes a grounded support layer, not a second hidden evaluator

Recommended role for gap analysis:

- grounded skill/requirement explanation
- overclaim-risk detection
- CV emphasis support
- debug artifact for why the CV was composed a certain way

To make that role trustworthy, gap analysis should consume only fields and evidence inputs that are explicitly owned by upstream stage contracts.

Gap analysis may emit:

- matched requirements
- missing requirements
- overclaim-risk signals
- grounded emphasis guidance
- explanatory notes for debug/export

Gap analysis should not emit:

- the primary user-facing ranking fit label
- a second hidden eligibility decision by default

Not the default role:

- second independent fit classifier that can contradict reranking

If deterministic fit should influence ranking, that must be explicit:

- either compute a true `gap_match_score` and feed it into ranking
- or keep gap as explanation only

But the system should not continue with:

- AI fit label in one place
- gap fit label in another
- ad hoc reconciliation logic later

### Stage 5: Validation should own artifact acceptance, not fit evaluation

Validation should remain the final acceptance check for generated CVs.

Its job is:

- section completeness
- grounding/provenance
- structural validity
- accepted/rejected artifact decision

It should not also act as a hidden fit filter.

### Stage 6: Debug/export surfaces should expose stage-local truth

Exports and debug artifacts should show:

- raw retrieval signals
- scoring shortlist signals
- primary ranking fit
- gap explanation
- validation result
- final artifact status

But they should not force the reader to reverse-engineer which stage “really decided” the outcome.

## Options Considered

### Option 1: Keep the current layered system and patch contradictions case by case

Pros:

- smallest rollout
- low immediate code churn

Cons:

- preserves overlapping authority
- keeps debugging hard
- encourages more reconciliation logic over time

Verdict:

- not recommended as the primary design

### Option 2: Keep the layered pipeline, but give each layer one explicit authority

Pros:

- preserves current product behavior shape
- reduces contradictions without redesigning the whole stack
- makes exports/debug much easier to trust

Cons:

- requires cleanup across several modules
- some current config/docs must be corrected

Verdict:

- recommended

### Option 3: Collapse evaluation into a single monolithic scorer

Pros:

- simplest mental model

Cons:

- loses useful deterministic safety and explanation layers
- makes debugging weaker
- over-couples ranking and CV composition

Verdict:

- not recommended

## Cleanup Workstreams

### Workstream A: Align ranking implementation with ranking contract

Phase 1 decision:

- reduce the active ranking contract to the features actually computed and used at runtime
- remove or mark unsupported configured ranking features as inactive

Do not expand runtime ranking feature computation in the same rollout unless those features already have clean upstream ownership and trusted inputs.

### Workstream B: Choose one primary fit label authority

Recommended first rollout:

- ranking fit label comes from AI scoring
- gap analysis no longer produces the user-facing primary fit label by default
- gap output remains available in debug/CV generation as explanation

This means:

- reranker fit owns the authoritative ranking fit label
- gap analysis may emit only secondary explanation/risk outputs

### Workstream C: Decide whether AI reranking is evidence-grounded in practice

Phase 1 decision:

- remove the evidence-grounded claim from the active reranker contract for now
- unless real runtime evidence can already be provided without introducing a new retrieval dependency into ranking

Do not keep the current state where the code contract implies evidence grounding but the runtime path usually provides no evidence.

### Workstream D: Align structured validation ownership

Phase 1 decision:

- one shared config-driven section contract governs both structured normalization and markdown validation
- semantic completeness checks remain bounded and apply only to enabled required sections

This especially matters for empty-but-present sections such as Summary.

Also make one section contract authoritative across:

- structured CV normalization
- rendered markdown validation
- config-driven composition rules

### Workstream E: Align config keys and runtime readers

Any documented config key used in ranking or validation must be the same key runtime reads.

This is a cleanup task, but it also matters because it affects whether settings actually work.

This includes:

- ranking null/default value keys
- retrieval shortlist sizing keys
- any future shared setting that currently has more than one runtime reader name

### Workstream F: Align gap-analysis inputs with real runtime ownership

Phase 1 decision:

- canonical years inputs are `years_experience_min` and `years_experience_max`
- legacy `years_required` should be removed from the active runtime contract or treated only as a backward-compatibility adapter during transition
- dormant evidence-aware overclaim paths must either be activated explicitly in runtime or removed from the active contract for now

Do not keep the current state where:

- the function surface suggests richer gap evaluation
- but runtime only partially supplies the required inputs

## Risks

### Behavior-change risk

Changing fit authority can alter which jobs get CVs.

Mitigation:

- keep rollout bounded
- compare old and new artifacts on the same run fixtures
- prefer explicit stage semantics over implicit reconciliation

### Ranking drift risk

Making ranking actually use all configured features may reorder jobs.

Mitigation:

- stage this separately
- add ranking regression fixtures
- inspect score decomposition in debug output

### Debug contract drift risk

During transition, exports/debug JSON may temporarily expose both old and new semantics.

Mitigation:

- version doc updates carefully
- keep fields explicit about stage and origin

### Scope creep risk

This cleanup can expand into a full ranking redesign if left unconstrained.

Mitigation:

- focus on authority, contract alignment, and contradiction removal first
- defer new scoring innovation until after cleanup

## Acceptance Criteria

- Ranking config, runtime ranking feature computation, and exported score semantics are aligned.
- The pipeline has one primary fit label authority for ranking/CV eligibility, and any secondary fit/explanation layer is explicitly secondary.
- Gap analysis no longer acts as a hidden competing evaluator unless that role is made explicit in ranking design.
- AI reranking is either truly evidence-grounded at runtime or its contract/docs are corrected to match reality.
- Gap analysis consumes only canonical, explicitly owned runtime inputs for years and overclaim evaluation.
- Validation policy is explicit about whether structured semantic completeness is enforced in addition to markdown section presence.
- Structured normalization and markdown validation use one coherent section-contract policy.
- Retrieval and ranking settings do not rely on duplicate config keys for the same concept.
- For any ranked job in export/debug surfaces, an operator can identify:
  - which stage determined shortlist inclusion
  - which stage produced the authoritative ranking fit label
  - whether CV generation was attempted or skipped
  - whether validation accepted or rejected the generated artifact
- Debug and export artifacts let an operator identify:
  - raw retrieval result
  - scoring shortlist result
  - primary ranking fit
  - gap explanation
  - validation result
  - final artifact status
- No saved run should require the reader to infer which of two competing fit systems “really won.”

## Out of Scope

- redesigning the enrichment model
- replacing vector search entirely
- replacing AI reranking with a fully deterministic ranking stack
- redesigning the CV schema
- redesigning the admin UI beyond what is needed to reflect clearer decision contracts

## Recommendation

Proceed with Option 2.

The cleanup should preserve the layered pipeline, but remove hidden overlap by making the contract explicit:

- retrieval selects candidates for scoring
- AI reranking owns primary ranking fit
- gap analysis explains grounded fit and supports CV composition
- validation owns artifact acceptance
- exports/debug surfaces expose each stage without semantic ambiguity

That gives the system a much clearer mental model and should remove the most confusing contradictions without forcing a full pipeline rewrite.
