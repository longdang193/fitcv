---
aliases: []
status: []
time: 2026-05-17-14-27-14-24
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
# rule_filter - inputs-outputs

START

T-F_Obsidian-v2

Q: rule_filter stage - Inputs and outputs: What information enters this stage, and what should come out?

A: In: enriched rows + policy + synonym map. Out: passed/rejected sets, reject reasons, marks, artifacts.

E: Source-grounded in docs/stages/rule_filter.yaml. Strong answer should include why, contract boundaries, and downstream impact.

END
