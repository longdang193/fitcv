---
aliases: []
status: []
time: 2026-05-17-12-27-11-6
tags:
  - "#interview-prep"
  - "#ANKI"
TARGET DECK: FITCV::INTERVIEW
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
# Run Summary Vs Item Observability Split

START

T-F_Obsidian-v2

Q: Why separate run-summary observability from item-level observation?

A: Run-summary surfaces explain overall run health and lifecycle behavior, while item-level observation captures per candidate-job IO and reasoning metadata. Split avoids payload bloat and preserves focused debugging paths.

E: What interviewer is testing: observability architecture judgment. Strong structure: failure of single-layer logging -> two-layer ownership -> operator benefit. Source-grounded points: explicit two-layer model and non-duplication rule (docs/pipeline.md). Weak answer: "cleaner logs." Follow-up: When would you intentionally surface item signal in run summary?

END
