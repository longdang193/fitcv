# Reproduction Steps

1. Open `reuse_control_findings.md`.
2. Confirm reuse lanes list includes enrichment, embedding, AI score, analysis, triage.
3. Confirm only one operator-facing toggle listed: `synonym_management.triage_recommendation_reuse_enabled`.
4. Confirm gap section states no explicit controls for other lanes.
5. Conclude contract drift between runtime behavior and settings surface.

## Command

```powershell
Get-Content reuse_control_findings.md
```
