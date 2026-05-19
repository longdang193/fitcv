---
aliases: []
status: []
time: 2026-05-19-00-29-32-8
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

## normalize - dependencies

SSTART

T-F_Obsidian-v2

Q: normalize stage - Dependencies: What does this stage rely on from earlier stages, and what later stages rely on it?

A: Relies on trigger input integrity; all downstream stages rely on normalized deduped pool.

E: Source-grounded fact: See docs/stages/normalize.yaml for this stage contract. Interview explanation: Explain why this decision exists, tradeoffs it introduces, and downstream impact.
EEND


