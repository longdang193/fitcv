---
name: live-run-prompt
description: Plan, preflight, execute, verify, diagnose, and close a live run.
distribution_tier: starter_kit
---

# Live Run Prompt

Define scenario and success checks. Run preflight. Execute once. Verify outputs.

For managed failure, classify admission versus terminal state before any follow-up.
For current leased-packet terminal evidence, external signed or legacy closure
uses `terminalize_attempt(evidence)`; personal-local closure uses
`harness-core-launcher close`. Host never writes `run.json`. Expired live or
unverified process state is `orphaned`, not retryable work.
Resume only an existing `planned` attempt through provider `--run-id`. Preserve a
terminal `blocked` run; after repair, require approved successor plan/task
identity and create a fresh request. Do not rerun a terminal managed run.

Close with run evidence, data-quality result, remaining risks, and next action.
