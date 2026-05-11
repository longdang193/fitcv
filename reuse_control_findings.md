# Reuse-Control Findings

## Summary
FitCV currently has multiple reuse lanes in execution code, but only one confirmed operator-facing runtime setting to disable reuse.

## Reuse lanes present in code
- enrichment reuse
- candidate query embedding reuse
- AI score reuse
- analysis reuse
- triage recommendation reuse

## Confirmed runtime setting exposed
- `synonym_management.triage_recommendation_reuse_enabled`

## Gap
No confirmed operator-facing per-run settings were found for:
- enrichment reuse disablement
- query embedding reuse disablement
- AI score reuse disablement
- analysis reuse disablement

## Impact
Current control-plane contract is inconsistent:
- execution behavior supports multiple reuse lanes
- settings surface exposes only one explicit reuse toggle

## Practical consequence
For current live-run validation:
- triage recommendation reuse can be disabled by `config_overrides`
- other lanes can only be made fresh indirectly today, such as using a fresh SQLite database state

## Deferred follow-up
Later work should decide whether to:
1. add explicit per-lane reuse settings
2. add one global `disable_all_reuse` control
3. keep indirect freshness strategy and document limits clearly
