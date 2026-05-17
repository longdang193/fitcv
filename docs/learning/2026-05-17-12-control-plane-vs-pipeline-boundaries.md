---
aliases: []
status: []
time: 2026-05-17-12-27-11-3
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
# Control Plane Vs Pipeline Boundaries

START

T-F_Obsidian-v2

Q: Explain architecture boundaries between src/fitcv_cp and src/fitcv.

A: src/fitcv_cp owns operational control surfaces (trigger, lifecycle, settings, UI/API, persistence adapters). src/fitcv owns pipeline stage semantics, decision logic, and stage artifact truth. This split prevents operational interfaces from redefining business decisions.

E: What interviewer is testing: ownership boundaries and coupling discipline. Strong structure: ownership -> allowed dependencies -> forbidden behavior. Source-grounded points: architecture layer split (docs/architecture.md), forbidden control-plane decision authority (docs/component_boundaries.md). Weak answer: "one side is backend and one side is AI." Follow-up: Name bug class this boundary prevents.

END
