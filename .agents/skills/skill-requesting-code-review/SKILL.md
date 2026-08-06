---
name: skill-requesting-code-review
description: Use when completed code changes need independent review before further implementation, handoff, merge, or release.
required_reads: []
distribution_tier: starter_kit
---
# Requesting Code Review

Use controller-selected `normal` or `high` reviewer. Give reviewer exact
requirements, base ref, allowed paths, current diff, and available proof.

Reviewer is read-only. Reviewer returns findings as `claimed_result`; harness
verification remains independent. Do not require commits or commit ranges.

Use `code-reviewer.md` packet. Controller decides repair, escalation, or
acceptance after harness evidence.
