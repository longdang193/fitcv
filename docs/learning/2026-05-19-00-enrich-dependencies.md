---
aliases: []
status: []
time: 2026-05-19-00-29-33-18
tags:
  - "#interview-prep"
  - "#pipeline-stage"
  - "#ANKI"
TARGET DECK: FITCV::PIPELINE-STAGES
question_type: qa
learning_mode: interview
bloom_level: auto
source_scope: repo
---

## enrich - dependencies

SSTART

T-F_Obsidian-v2

Q: enrich stage - Dependencies: What does this stage rely on from earlier stages, and what later stages rely on it?

A: Depends on normalize; downstream policy/scoring/generation depend on enriched semantics.

E: Source-grounded fact: See docs/stages/enrich.yaml for this stage contract. Interview explanation: Explain why this decision exists, tradeoffs it introduces, and downstream impact.
<!--ID: 1779144736212-->
EEND


