---
aliases: []
status: []
time: 2026-05-17-14-27-14-7
tags:
  - "#interview-prep"
  - "#pipeline-stage"
  - "#ANKI"
TARGET DECK: FITCV::PIPELINE-STAGES
question_type: qa
learning_mode: interview
bloom_level: auto
source_scope: repo
validation:
  one_question_per_file: true
  required_tokens:
    - START
    - T-F_Obsidian-v2
    - END
  requires_title: true
  requires_explanation: true
  requires_answer_field: true
---
# normalize - failure-modes

START

T-F_Obsidian-v2

Q: normalize stage - Failure modes: What can go wrong in this stage, and how would we detect or prevent it?

A: False merge or missed duplicate; detect via artifacts and downstream anomalies; prevent with tests/rules.

E: Source-grounded in docs/stages/normalize.yaml. Strong answer should include why, contract boundaries, and downstream impact.

END
