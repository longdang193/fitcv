---
aliases: []
status: []
time: 2026-05-17-12-27-11-5
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
# Backend Portability And AI Routing Invariants

START

T-F_Obsidian-v2

Q: What are key runtime invariants around backend portability and AI routing?

A: Storage backend choice (sqlite vs bigquery) must affect persistence behavior only, not AI provider/model decisions. AI stage routing authority comes from control_plane.model_routing.parts.*, and missing route/auth must fail fast.

E: What interviewer is testing: contract-level thinking and invariance reasoning. Strong structure: invariant -> authority -> enforcement/failure mode. Source-grounded points: pipeline invariance rules and fail-fast contract (docs/pipeline.md), routing config owner (config/runtime/control_plane.yaml, docs/configuration.md). Weak answer: "supports two backends." Follow-up: What test catches backend-dependent AI drift fastest?

END
