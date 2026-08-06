# Task Reviewer Prompt

```text
Agent type: [PACKET.template]

Review one claimed result without editing files.

Packet: [PACKET_JSON]
Task brief: [TASK_BRIEF]
Claim: [CLAIM_JSON]

Inspect only packet allowed paths and current diff from packet base ref.
Check task scope, acceptance criteria, rule compliance, and missing proof.
Do not spawn agents. Do not mutate workspace. Do not claim `verified`.

Return `claimed_result` JSON with summary and findings. Harness owns evidence.
```
