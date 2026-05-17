---
aliases: []
status: []
time: 2026-05-17-12-27-11-4
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
# Effective Settings Resolution Per Run

START

T-F_Obsidian-v2

Q: Walk through effective settings resolution for one run.

A: Resolution order is: base config_path load, persisted active settings overlay, run-scoped overrides, derived compatibility recompute, then persist effective snapshot as settings-used.json for run truth and reproducibility.

E: What interviewer is testing: config precedence, mutability boundaries, reproducibility. Strong structure: ordered precedence + what mutates future vs current run + evidence artifact. Source-grounded points: explicit 6-step resolution and run snapshot contract (docs/configuration.md). Weak answer: "overrides win." Follow-up: Why persist effective settings, not only raw overrides?

END
