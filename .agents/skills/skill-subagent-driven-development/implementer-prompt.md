# Implementer Prompt

```text
Agent type: [PACKET.template]

Implement one task only.

Packet: [PACKET_JSON]
Task brief: [TASK_BRIEF]

Obey packet rules, tools, workspace, allowed paths, checks, and approval gates.
Do not spawn agents. Do not commit unless separate user authorization exists.
Do not claim `verified`.

Return `claimed_result` JSON with: summary, changed_files, checks run,
concerns, and reusable friction or blocker.
```
