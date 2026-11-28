# Tasks

- [x] 1. Harden partial-ranking eligibility: prioritize explicit technical failure counters and require a complete validated ranking-to-CV handoff for continuation.
- [x] 2. Derive terminal checkpoint stage fields from the actual failing stage; add failure-stage and retry-boundary regressions.
- [x] 3. Persist typed scorer diagnostics through the ranking artifact and failed stage settlement, and prove parser-to-persisted-artifact propagation plus stale-field clearing on success.
- [x] 4. Bound and sanitize persisted diagnostics; persist typed CV-generation failure summaries and latest status in per-job/stage records.
- [x] 5. Run focused backend tests, relevant broader tests, and strict OpenSpec validation; inspect the final diff and repository status.
