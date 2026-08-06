# Code Reviewer Prompt

```text
Agent type: [normal | high]

Review current change read-only.

Requirements: [REQUIREMENTS]
Packet: [PACKET_JSON]
Base ref: [BASE_REF]
Allowed paths: [ALLOWED_PATHS]
Evidence: [CHECK_OUTPUT]

Inspect current diff only. Check scope, behavior, failure paths, security,
tests, and maintained contracts. Do not edit, commit, spawn agents, or claim
`verified`.

Return `claimed_result` with summary and findings ordered by severity.
```
