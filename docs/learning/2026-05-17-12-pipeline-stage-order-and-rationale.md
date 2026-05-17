---
aliases: []
status: []
time: 2026-05-17-12-27-11-2
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
# Pipeline Stage Order And Rationale

START

T-F_Obsidian-v2

Q: Why must stage order stay normalize -> enrich -> rule_filter -> shortlist -> ranking -> cv_analysis -> cv_generation?

A: Order enforces dependency and spend control: early normalization/enrichment establish clean inputs, rule_filter removes deterministic fails before expensive retrieval and AI steps, ranking sets fit decisions before evidence-heavy analysis and generation.

E: What interviewer is testing: dataflow reasoning and architectural intent. Strong structure: dependency -> cost/risk -> consequence of reordering. Source-grounded points: canonical order and responsibilities (docs/pipeline.md), deterministic gates before expensive stages (README). Common weak answer: "legacy order." Follow-up: If latency is critical, which stage do you optimize first and why?

END
