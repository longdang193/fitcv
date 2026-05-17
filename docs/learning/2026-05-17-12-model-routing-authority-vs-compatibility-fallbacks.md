---
aliases: []
status: []
time: 2026-05-17-12-27-11-8
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
# Model Routing Authority Vs Compatibility Fallbacks

START

T-F_Obsidian-v2

Q: Why put model routing defaults in control-plane config while pipeline config still has fallback model fields?

A: Control-plane model_routing is canonical routing authority for AI stages. Pipeline model fields remain compatibility fallbacks during migration to avoid breaking older paths while converging to a single source of truth.

E: What interviewer is testing: migration strategy and backward-compat trade-offs. Strong structure: canonical owner -> temporary compatibility layer -> removal condition. Source-grounded points: docs/configuration ownership matrix and pipeline fallback comments (docs/configuration.md, config/runtime/pipeline.yaml). Weak answer: "legacy leftovers." Follow-up: What objective signal says fallback can be removed?

END
