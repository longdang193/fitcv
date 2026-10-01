# FitCV Approved P0/P1 Finalization Evidence

Date: 2026-10-01
Owner: lead controller
Plan: `docs/superpowers/plans/2026-10-01-fitcv-approved-p0-p1-finalization-plan.md`

## Implemented

- Render acceptance is isolated from ordinary Full Suite and runs on Ubuntu
  `24.04` with native `pandoc`, `xelatex`, and Poppler tools.
- P0-B evaluator fails closed on incomplete evidence-link review, missing
  approved support threshold, contradictory review rows, invalid projection
  links, and unsupported reviewer provenance.
- Benchmark outputs expose named relevance/error counters and calibration loss
  buckets.
- P0-A v4 closeout hashes now match committed bytes; v3 history remains
  unchanged.
- Responsibility support uses direct source fragments, preserves fragment
  boundaries, feeds final `requirement_coverage`, and supports bounded verified
  recovery without increasing configured pool size.

## P0-B Decision

Status: `not_promotable`

The qualifying package has `212` reviewed requirement rows across `25` source
groups, but both reviewer records declare `human_identity_verified: false`.
The package therefore fails the approved independent-review provenance gate.
No holdout promotion or production-default change occurred.

The diagnostic evaluator also remains ineligible:

| Metric | Result | Gate |
|---|---:|---:|
| Selected requirement recall | `29/143 = 0.202797` | `>= 0.80` |
| Minimum source-group recall | `0.0` | `>= 0.60` |
| Incorrect pairs | `0` | `0` |
| Hard-negative false positives | `6` | `0` |
| Support-recall threshold | missing | required |
| Overall eligibility | `false` | pass all |

The `212`-row source-backed package remains diagnostic only. Do not tune or
promote from this run.

## P0-A Provenance

The v4 manifest and closeout references resolve to current committed bytes.
The closeout decision remains `evaluated_not_promoted`; production defaults
remain unchanged.

## P1-A / P1-B Evidence

- Render acceptance: `3 passed` under marker `render_acceptance`.
- Sanitized workload: `p1b-approved-sanitized-001`.
- Persisted run status: `succeeded`; checkpoint: `completed`.
- Review path: `regenerate_once` then `approve_as_is`.
- Event stages include `cv_regenerate_once_requested` and
  `cv_review_completed`.
- Final artifact version:
  `012c8ce2-17a2-5a74-8eda-e0fe8c99cd82`.
- Accepted effort schema: `accepted_cv_effort_v1`; denominator:
  `accepted_cv_count = 1`.
- The denominator is reproduced by `build_accepted_cv_effort_projection` from
  persisted SQLite run compatibility data plus its persisted review actions;
  this is the authoritative derived acceptance projection.
- Provider calls: `1`; regeneration count: `1`; human action count: `2`.
- Token usage remains `not_run`; no efficiency claim is made from one sample.
- P1-C and P2 remain deferred.

## Hashes

| Artifact | SHA-256 |
|---|---|
| `.tmp/p0b-final-evaluation.json` | `bbf06777e78adfc62fa89efa3b5f8819f8a40921694a8d612c9e5b556869bc47` |
| `scripts/evaluate_p0b_source_job_relevance.py` | `a81e0d83c61dabb3f0b6e0cedafb23041c78d629d1b6a35f69d43bbe70ff2e18` |
| `config/policy/cv_analysis.yaml` | `3630144170991755df78a62a308e9d56cd182fa726bfb7edbdfd16e25b7d81ae` |
| `data/fitcv-p0-corpus/p0b/p0b_source_job_relevance_fixture_v2_human_frozen.json` | `6b9ab2cacd3bf72d4eec7ebb2c137c17b637a1c63ced606cd913241948e4a28c` |
| `data/fitcv-p0-corpus/p0b/p0b_source_job_review_packet_v2_human_adjudicated.json` | `48fc695e63988784925885895e00bef3279fed60990e6f8cec538e1c106fc8ac` |
| `data/fitcv-p0-corpus/p0b/p0b_source_job_source_group_map_v2.json` | `20e983a8c93eba3bfa0ff39756b0afdaa0f43ec4bfa0415931105e43f8d416a9` |
| `.tmp/p1b-approved-workload/evidence.json` | `48d1e575c0ff0740a4c6d4c4e4afa388d4c303b6128ee10d8793009192ff0411` |
| `.tmp/p1b-approved-workload/control-plane.sqlite3` | `3706cd8e6c046042f8e3b056307d8fcfd71e310ea7d4e05becbff952ab6e7b7f` |

## Verification

- `2966 passed, 4 skipped, 3 deselected` under `-m "not render_acceptance"`.
- `3 passed` under `-m render_acceptance`.
- P0/P1 focused suites pass after direct-support and recovery changes.
- Workflow YAML parse passes.
- `git diff --check` passes.
