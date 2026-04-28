---
layer: change
artifact_type: spec
status: proposed
parent_thread: workstream-agentic-synonym-management.agentic-synonym-proposal-engine
targets:
  - docs/intent/workstreams/threads/workstream-agentic-synonym-management/02-agentic-synonym-proposal-engine.md
  - src/fitcv/pipeline.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/app.py
  - src/fitcv/rule_filter.py
  - config/taxonomy/skill_synonyms.yaml
related_features:
  - trigger_run_management
  - inspection_debugging
  - settings_system
related_stages:
  - enrich
  - rule_filter
---

# Agentic Synonym Proposal Engine

## Summary

Define the bounded proposal-object contract for synonym assistance so candidate
alias-to-canonical mappings, clusters, confidence, rationale, and review-ready
metadata can be generated consistently before any operator review surface is
designed around them.

This spec follows the first-wave semantic and operator-truth specs. It keeps
synonym assistance review-first: proposal generation may recommend mappings, but
it must not silently mutate shared canonical synonym state.

## Triage

Layer: `change`  
Feature type: `ADD`

Reasoning:

- this is the Wave 4 detailed spec named by the approved first-wave authoring
  map
- it comes after the semantic, outcome, observability, analysis-grounding, and
  operator-truth specs so the proposal object can reuse stable vocabulary
- it is bounded to proposal generation, not the review UI itself

Invariants:

- the shared canonical synonym config remains human-approved truth
- proposal generation is advisory until an operator approves a bounded change
- run-scoped overlays stay distinct from shared default config
- proposal objects must be stable enough for later queue, approval, and impact
  preview surfaces

Dependencies:

- `docs/intent/workstreams/threads/workstream-agentic-synonym-management/02-agentic-synonym-proposal-engine.md`
- `docs/superpowers/specs/2026-04-28-fitcv-semantic-spine-stage-authority-contract-spec.md`
- `docs/superpowers/specs/2026-04-28-deterministic-truth-outcome-contract-spec.md`
- `docs/superpowers/specs/2026-04-28-operator-control-plane-run-detail-truth-spec.md`
- `src/fitcv/pipeline.py`
- `src/fitcv_cp/worker_job.py`
- `src/fitcv_cp/app.py`
- `config/taxonomy/skill_synonyms.yaml`

Primary lens: `mixed`

Generated refresh required: `yes` after the spec is added, because
`docs/generated/planning_lineage.yaml` derives thread-to-spec lineage from
`parent_thread`.

Plan needed: `no` until the shared review-surface spec is drafted and the
proposal object is approved.

## Problem

The repo already has early synonym-assistance ingredients:

- canonical synonym config in `config/taxonomy/skill_synonyms.yaml`
- mapping suggestions collected from enriched rows in `src/fitcv/pipeline.py`
- immutable run-scoped mapping suggestion snapshots persisted through
  `src/fitcv_cp/worker_job.py`
- aggregate inspection and overlay upload surfaces in `src/fitcv_cp/app.py`

What it does not have yet is a first-class proposal-object contract. Without
that, later review surfaces would be forced to infer proposal identity and
meaning from loosely aggregated mapping suggestions.

## Goals

- define one bounded proposal object that later review surfaces can trust
- separate candidate discovery from approval and promotion
- preserve confidence and rationale without pretending proposals are final truth
- support both run-scoped overlay adoption and later shared-canonical promotion

## Non-Goals

- no operator review queue UI in this spec
- no automatic mutation of `config/taxonomy/skill_synonyms.yaml`
- no downstream impact preview yet; that belongs to a later thread

## Proposed Contract

## 1. Proposal Identity

Each proposal should have a stable bounded identity.

Required identity fields:

- `proposal_id`
- `run_id` when generated from one run
- `proposal_scope`
- `proposal_family`

Rules:

- `proposal_id` must be stable enough that review actions can reference it later
- `proposal_scope` distinguishes:
  - `run_scoped_overlay_candidate`
  - future shared-canonical promotion candidates
- `proposal_family` distinguishes whether the proposal is:
  - one alias-to-canonical mapping
  - one multi-alias cluster
  - one conflict or ambiguity bundle

## 2. Canonical Proposal Object

Every review-ready proposal object should be able to expose:

- `proposal_id`
- `run_id`
- `alias`
- `canonical`
- `candidate_aliases`
- `candidate_canonicals`
- `confidence`
- `rationale`
- `evidence_summary`
- `conflict_summary`
- `proposal_status`
- `proposal_scope`
- `source_artifact_refs`

Rules:

- `alias` and `canonical` should be lowercase normalized comparison surfaces
- `candidate_aliases` and `candidate_canonicals` support cluster or ambiguity
  cases without requiring a different object family later
- `proposal_status` should begin as a review-first state such as
  `proposed_unreviewed`

## 3. Confidence Contract

The current runtime already preserves suggestion confidence in mapping
suggestions and aggregate views. This spec turns that into a first-class
proposal field.

Rules:

- `confidence` expresses proposal strength, not approval state
- confidence must remain bounded and numeric enough for sorting and thresholding
- low-confidence proposals remain valid review objects if their rationale is
  informative
- confidence alone must not authorize automatic promotion

## 4. Rationale Contract

Every proposal should preserve why it exists.

Minimum rationale families:

- repeated alias-to-canonical suggestion across jobs
- repeated co-occurrence in enriched mapping suggestions
- conflict detection where one alias maps to multiple candidate canonicals
- bounded run-specific context such as occurrence count and average confidence

Rule:

- rationale should be explainable from existing run-scoped suggestion payloads,
  not fabricated summary text with no source anchors

## 5. Evidence Summary Contract

Review-first proposals need bounded evidence, not raw dumps.

`evidence_summary` may include:

- occurrence count
- average confidence
- bounded conflicting-canonical list
- representative source refs such as run id or enriched-job sample count

It should not inline:

- full job descriptions
- whole enriched artifacts
- full overlay yaml bodies

## 6. Conflict And Ambiguity Handling

The proposal engine must not force every signal into a simple alias-to-canonical
mapping if the evidence is genuinely mixed.

Required ambiguity support:

- one alias with multiple plausible canonicals
- one canonical family with multiple aliases that may belong in one cluster
- proposals that should be review-held because conflict is meaningful

Rule:

- ambiguous cases remain proposals; they do not become hidden defaults

## 7. Relationship To Run-Scoped Overlay

The proposal engine should support run-scoped overlay creation without making
overlay application synonymous with global approval.

Proposal-to-overlay rules:

- proposals may be selected into a run-scoped overlay
- run-scoped overlay application affects one run’s effective config
- run-scoped overlay approval does not automatically change the shared default
  synonym file

This preserves a clean ladder:

- proposal generation
- operator review
- optional run-scoped overlay adoption
- optional later shared-canonical promotion

## 8. Persistence Contract

The current repo already persists mapping suggestions as immutable run-scoped
snapshots. The proposal engine should treat those as upstream input surfaces,
not as the final review-object storage format.

Rules:

- run-scoped suggestion snapshots remain source evidence
- later review surfaces may derive proposal objects from them
- proposal-object persistence should preserve canonical fields needed for review
  actions without requiring the whole raw suggestion history to be re-read every
  time

## 9. Relationship To Shared Review Surface

This spec intentionally stops before queue and approval design.

It defines:

- what the review object is
- which fields it must preserve
- how confidence, rationale, and ambiguity work

The next shared review spec will define:

- how proposals are listed
- how approvals or rejections are recorded
- how selected proposals become run-scoped overlays

## Acceptance Criteria

- a reviewer can inspect one proposal object and understand the suggested alias,
  canonical target, confidence, rationale, and ambiguity state
- proposal objects are review-ready without mutating shared canonical config
- proposal identity is stable enough for later queue and approval actions
- run-scoped overlay adoption can build on the proposal object without changing
  its semantics

## Risks

- if proposal objects are too thin, the review queue will have to reconstruct
  meaning from raw mapping-suggestion payloads
- if proposal objects are too heavy, they will duplicate full run artifacts and
  become cumbersome
- if confidence is treated as approval, operators will lose the safety boundary
  between suggestion and adoption

## Next Artifact

The immediate next detailed spec should be:

- `docs/superpowers/specs/2026-04-28-agentic-synonym-review-queue-and-operator-actions-spec.md`

After both specs are approved, the next orchestration artifact should be an
implementation execution map for the approved subset that is ready to build.
