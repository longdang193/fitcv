# FitCV Final P0/P1 Acceptance Integrity Closure

Date: 2026-10-02
Base commit: `3af97052dedd168fe5128731671e039b16268b6f`
Plan: `docs/superpowers/plans/2026-10-02-fitcv-final-p0-p1-acceptance-integrity-closure-plan.md`

## Decision

- P0-A: `rejected`; retained as closed negative experiment.
- P0-B: `passed`; runtime evaluator is promotable against frozen sanitized inputs.
- P0-C: `passed`; strict mandatory qualifiers fail closed while bounded related-field education matches pass.
- P1-A: `maintenance_only`.
- P1-B: `passed`; automatic and human-confirmed accepted artifacts share one idempotent effort projection.
- P1-C: `deferred`.
- P2: `deferred`.

## Supersedes

This evidence supersedes stale status or scope claims in:

- `docs/superpowers/evidence/2026-10-01-fitcv-approved-p0-p1-finalization.md`
- `docs/superpowers/evidence/2026-10-01-fitcv-final-p0-p1-closure.md`
- `docs/superpowers/evidence/2026-10-01-fitcv-task9-closure.md`
- `docs/superpowers/evidence/2026-10-01-fitcv-p0-p1-execution.md`
- `docs/superpowers/evidence/2026-10-01-fitcv-p1b-historical-measurement.md`
- `docs/superpowers/evidence/2026-10-02-fitcv-p1b-live-measurement.md`

Historical files remain unchanged for audit history. `config/acceptance_state.yaml`
is current machine-owned status.

## P0-B

Runtime command:

```text
python -m scripts.evaluate_p0b_source_job_relevance --projection data/fitcv-p0-corpus/p0b/candidate_evidence_projection_source_backed_v1.jsonl --evidence-link-review data/fitcv-p0-corpus/p0b/p0b_source_job_evidence_link_review_v1.csv --oracle data/fitcv-p0-corpus/p0b/p0b_source_job_support_oracle_v1.jsonl --policy config/policy/cv_analysis.yaml --acceptance-state config/acceptance_state.yaml --output .tmp/p0b-runtime-final-explicit.json
```

Output: `.tmp/p0b-runtime-final-explicit.json`.

| Gate | Result |
|---|---:|
| Candidate requirement recall | `1.0` |
| Selected requirement coverage | `1.0` |
| Assignment precision | `1.0` |
| Unsupported or unknown assignments | `0` |
| Oracle coverage | `1.0` |
| Review completeness | `1.0` |
| Eligible | `true` |
| Status | `promotable` |

All-negative requirements remain in evaluated assignment accounting. The output
records `evaluated_commit`, `evaluated_worktree_dirty`, and frozen input hashes;
`evaluation_freeze_commit` continues to identify the frozen corpus/policy
inputs. Before commit, `evaluated_worktree_dirty` must be read as provenance
metadata, not as a clean-commit claim.

## P0-C

`tests/test_evidence.py` covers strict negative cases for:

- Computer Science versus International Business degree field.
- Claude Code versus generic coding tool.
- Executive search versus generic market research.
- Three years Kubernetes versus one year.

The same suite covers positive bounded cases, including a degree in a related
field when the requirement explicitly says `related field`. Latest focused
P0-C proof: `120 passed`.

## P1-B

Automatic and human-confirmed accepted artifacts now persist through
`accepted_cv_artifact.v1`. Replay deduplicates artifact events and actions.
`accepted_cv_effort_v1` joins top-level `cv_generation_trace.records` and keeps
all contributing attempts, provider calls, validation failures, regeneration,
render retries, review questions, human actions, reused resolutions, token
totals, elapsed time, and failure categories.

Synthetic live-workload baseline:

| Measure | Result |
|---|---:|
| Attempted generation jobs | `17` |
| Accepted artifacts | `11` |
| Validation failures | `6` |
| Regenerations | `9` |

Latest P1-B contract proof: `20 passed`. The existing live workload preserves
the `17 / 11 / 6 / 9` baseline and does not claim general performance
improvement.

## Fresh verification

- Focused closure suite: `948 passed, 4 skipped`.
- Full Suite (`-m "not render_acceptance"`): `2992 passed, 8 skipped, 4 deselected`.
- Focused Smoke Tests: `716 passed`.
- Render Acceptance: `4 passed`.
- Public corpus integrity: `6 passed`.
- Clean sparse checkout: acceptance-state rendering, P0-B runtime evaluation,
  public corpus test, and `git diff --check` passed.
- `git diff --check` passed for clean checkout; local checkout reports only the
  existing Windows LF/CRLF normalization warning for `src/fitcv/pipeline.py`.
- Adapter sync is not applicable: repository has no adapter mapping or adapter
  directory, matching workflow skip conditions.

## Residual scope

P1-C and P2 remain explicitly deferred. No new service, agent, datastore,
graph, vector store, management surface, or performance optimization is part
of this closure.
