# FitCV P1-B Live Measurement Evidence

Date: 2026-10-02
Owner: lead controller
Plan: `docs/superpowers/plans/2026-10-02-00-15-fitcv-p0-p1-completion-plan.md`

## Scope

Executed source-backed local workload from
`data/linkedin-2026-10-01-00-26-29.json` against isolated SQLite state at
`.tmp/p1b-live-workload/control_plane.sqlite3`.

The workload used four worker-owned runs:

| Run | Attempted | Accepted | Validation failures | Wall time (ms) |
|---|---:|---:|---:|---:|
| `p1b-live-5561c8ee5af7` | 7 | 4 | 3 | 136153.363 |
| `p1b-live-2-2006d7fe2a` | 4 | 3 | 1 | 135175.680 |
| `p1b-live-3-c5009eef24` | 2 | 1 | 1 | 128133.247 |
| `p1b-live-4-696a6df403` | 4 | 3 | 1 | 117090.540 |
| **Total** | **17** | **11** | **6** | — |

## `accepted_cv_effort_v1`

| Metric | Result |
|---|---:|
| Accepted CV denominator | `11` |
| Unique jobs | `11` |
| Runs | `4` |
| Acceptance rate | `11 / 17 = 0.647059` |
| Provider calls | `20` |
| Token usage | `available` for `11 / 11`; `101808` total tokens |
| Regeneration count | `9` |
| Review questions shown | `34` |
| Human actions | `not_applicable` for `11 / 11` auto-accepted artifacts |
| CV elapsed time | `291659 ms` total; `26514.455 ms` mean |
| Page fit | `11 / 11` passed; all rendered to `1` page |

Per-artifact measurement is preserved in
`.tmp/p1b-live-workload/accepted_cv_effort_v1.json`. Render evidence is in
`.tmp/p1b-live-workload/rendered-fixed/summary.json`; each PDF was produced with
`pandoc` and `xelatex`, then checked with `pdfinfo` and `pdftotext`.

## Decision

Measurement exists and meets sample size: `11` accepted CVs across `4` runs
and `11` jobs. Provider, token, regeneration, question, elapsed, and page-fit
fields are available. Auto-accepted pipeline artifacts have no persisted HITL
review rows, so human actions remain explicitly `not_applicable`; no action
values were fabricated.

P1-B is promotable: all 11 generated CVs pass the one-page render target and
pipeline acceptance outcomes are persisted. P1-C and P2 remain deferred.
