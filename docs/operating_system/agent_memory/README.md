# Agent Memory

This directory stores small, reusable agent memory for repo work.

Use it to preserve:

- stable invariants that should not be rederived every session
- recurring repo workflow patterns
- important failures that should become guardrails
- unresolved questions that may affect future agent behavior

This layer complements, but does not replace:

- feature and stage docs
- specs and plans
- repo-governance docs
- generated rules and adapter outputs

## Files

- `invariants.md`
  - consult when planning or changing repo structure
- `patterns.md`
  - consult for recurring operating-system and workflow tasks
- `failure-ledger.md`
  - consult during debugging, retries, or after important mistakes
- `open-questions.md`
  - consult when a reusable ambiguity may change agent behavior later

## Update Rules

- Keep entries short and operational.
- Add memory only when it is likely to help future sessions.
- Do not duplicate source-of-truth docs verbatim.
- When a failure repeats, turn it into a rule, test, script check, CI hook, or explicit follow-up.
