---
aliases: []
status: []
time: 2026-05-17-12-27-11-10
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
# Proof Of Testability Beyond Prompts

START

T-F_Obsidian-v2

Q: How do you prove this system is testable and not only prompt-driven?

A: FitCV has broad automated tests across pipeline logic, configuration, validators, and control-plane components, plus repository contract validation in normal hook workflows. This validates both runtime behavior and structural governance contracts.

E: What interviewer is testing: engineering rigor and verification discipline. Strong structure: test surfaces -> contract gates -> outcome. Source-grounded points: tests tree coverage and repo-contract validation workflow (tests/, docs/operating_system/governance/repo-governance.md). Weak answer: "we use pytest." Follow-up: Which missing test would raise cross-backend confidence most?

END
