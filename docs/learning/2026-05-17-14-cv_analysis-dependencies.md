---
aliases: []
status: []
time: 2026-05-17-14-27-14-58
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
# cv_analysis - dependencies

START

T-F_Obsidian-v2

Q: cv_analysis stage - Dependencies: What does this stage rely on from earlier stages, and what later stages rely on it?

A: Depends on ranking truth; cv_generation depends on immutable ready analysis records.

E: Source-grounded in docs/stages/cv_analysis.yaml. Strong answer should include why, contract boundaries, and downstream impact.

END
