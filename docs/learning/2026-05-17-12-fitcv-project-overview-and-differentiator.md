---
aliases: []
status: []
time: 2026-05-17-12-27-11-1
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
# FitCV Project Overview And Differentiator

START

T-F_Obsidian-v2

Q: Give 60-second overview of FitCV. What problem does it solve, and what makes this system different from generic CV tools?

A: FitCV addresses manual job-to-CV matching breakdown at scale by combining deterministic staged processing with bounded agentic AI and operator-visible evidence. It differs from generic CV tools by preserving stage-owned truth and deterministic acceptance gates while still improving late-stage quality with targeted AI seams.

E: What interviewer is testing: clarity, product framing, and ability to connect architecture to business outcomes. Strong answer structure: problem -> constraints -> solution -> tradeoff -> impact. Source-grounded points: manual workflow pain and staged pipeline with control plane (README), selective agentic upgrade with preserved deterministic semantics (docs/intent/project-charter.md). Common weak answer: "it uses AI to generate CVs." Better framing ties trust, auditability, and operator control to business value. Follow-up: Why not fully agentic end-to-end from first stage?

END
