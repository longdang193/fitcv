# Master Workstream Roadmap

## Purpose

This roadmap translates the current intent layer into the major delivery threads required to finish the FitCV-first agentic upgrade.

The end goal is:

- FitCV remains the authoritative end-to-end pipeline
- the original pipeline semantics, stage boundaries, and checkpoint meaning remain intact
- selective agentic AI improves bounded late-stage quality without replacing deterministic acceptance discipline
- operators can trigger, inspect, and trust the full run lifecycle without needing to infer hidden state

This roadmap separates product work from operating-system work so repo-method cleanup does not get mistaken for product completion.

## Product Workstreams

### 1. FitCV Semantic Spine

Keep the original FitCV pipeline meaning authoritative from input ingestion through final CV outcome.

This workstream owns:

- preserving original stage order and stage-owned boundaries
- keeping reranker and deterministic fit authority explicit
- preserving checkpoint and continue semantics
- aligning direct-input and manual-input paths to the same stage meaning as the original pipeline
- preventing replay-first or shadow-runtime behavior from becoming a second product identity

This is the primary spine. All other product workstreams depend on it.

### 2. Operator Control Plane

Preserve and strengthen the original control-plane experience so operators can run the system without terminal-first workflows.

This workstream owns:

- trigger inputs, run modes, and checkpoint continuation
- runs list and run detail as the authoritative operator surfaces
- stage progress, status truth, and lifecycle actions
- settings access, run controls, and download paths that match actual runtime ownership

This is product work, not operating-system work.

### 3. Deterministic Acceptance And Artifact Truth

Make every major decision legible and stage-owned so accepted, blocked, and rejected outcomes are explainable.

This workstream owns:

- stage-owned diagnostics and transition artifacts
- truthful results ledgers and decision chains
- accepted, held, blocked, and rejected late-stage narration
- inspection exports, settings-used exports, and provenance surfaces
- stable distinction between authoritative runtime decisions and supporting explanation

This workstream protects trust in the upgraded system.

### 4. Bounded Agentic CV Quality

Add selective agentic intelligence only where it improves late-stage FitCV behavior without breaking deterministic gates.

This workstream owns:

- grounded `cv_analysis` evidence selection and fit-readiness reasoning
- stronger `cv_generation` rewrite and repair behavior from analysis signals
- explicit pre-writing hold reasons
- bounded live-provider integration for agentic late-stage seams
- preservation of deterministic validation as the final acceptance gate

This is the main upgrade workstream, but it must stay subordinate to the semantic spine and deterministic acceptance workstreams.

### 5. Pipeline Efficiency And Reuse

Improve throughput and repeatability without weakening stage truth.

This workstream owns:

- exact-match reuse where stage-owned inputs still match
- bounded performance improvements before expensive late-stage work
- reuse diagnostics that stay truthful for operators
- keeping expensive CV work gated behind earlier narrowing and fit decisions

This workstream is valuable, but it is not allowed to distort product semantics.

## Operating-System Workstreams

These are necessary repo-enablement threads, but they are not the product itself.

### A. Docs And Contract Hygiene

Own the intent layer, stage source docs, feature source docs, generated discovery sync, and source-of-truth placement rules.

### B. Repo Governance And Publication Boundary

Own private-vs-public repo behavior, curated publication, and the rule that private operating-system material must not leak into the public mirror.

### C. Starter Shared-Surface Sync

Keep shared repo-control surfaces aligned with the adopted starter baseline without overwriting project-specific product meaning.

### D. Agent Workflow Reliability

Own skills, agent memory, adapter sync, validation scripts, and guardrails learned from repeated failure patterns.

## Missing Or Vague Top-Level Threads

The current intent docs were too thin in a few places. The main missing or vague threads were:

- no explicit semantic-spine thread to guard the original FitCV meaning
- no separate product thread for deterministic acceptance and artifact truth
- no clear distinction between operator product work and repo operating-system work
- no explicit bounded-agentic thread saying where agentic AI is allowed and where it is not
- no efficiency-and-reuse thread to keep performance work from being smuggled into semantic changes

## Sequencing

Recommended execution order:

1. FitCV Semantic Spine
2. Operator Control Plane
3. Deterministic Acceptance And Artifact Truth
4. Bounded Agentic CV Quality
5. Pipeline Efficiency And Reuse

Operating-system threads should run in parallel only when they reduce drift or unblock product truth, not as substitutes for product delivery.

## Completion Criteria

The roadmap is complete when:

- the upgraded line still behaves like FitCV in its stage meaning and acceptance rules
- operators can run and inspect the system through the original control-plane shape
- late-stage agentic behavior improves quality without becoming an unbounded second runtime
- artifacts, diagnostics, and exports tell the truth about what happened
- doc and repo-governance layers support the product without redefining it
