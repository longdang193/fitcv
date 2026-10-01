# FitCV Final P0/P1 Closure

Date: 2026-10-01
Base commit: `27e715f5784f63615dcd67bcfdfb7e29617576e0`

## Decision

- P0-A: `evaluated_not_promoted`; nested score-artifact references repaired and hash chain verified. Production defaults unchanged.
- P0-B: `not_promotable`; strict responsibility proof now maps all `12/12` accepted evidence pairs and passes support-gate checks at approved threshold `0.8`, but actual retrieval remains below promotion gates. No tuning or promotion applied.
- P0-C: `protected`; no qualifier-default change.
- P1-A: `verified`; render workflow uses Bash consistently and native PDF tools remain explicit.
- P1-B: `verified_bounded`; existing sanitized workload `p1b-approved-sanitized-001`, accepted denominator `1`, `regenerate_once`, `approve_as_is`, final artifact, `accepted_cv_effort_v1`.
- P1-C/P2: `deferred`.

## P0-B Evaluation

Command returned exit code `1`, as required for a failed gate. Output: `.tmp/p0b-final-check.json`.

- Input validation: passed; `212` rows, `25` source groups.
- Actual FitCV recall: `6/143` (`0.04195804195804196`); minimum source-group recall: `0.0`.
- Pair accounting: `12` true positives, `0` false positives, `0` false negatives for accepted responsibility links.
- Support review: clean against canonical source-backed projection; approved support threshold `0.8` passes with supported-link recall `1.0`. Overall P0-B remains blocked by actual retrieval gates and `6` hard-negative false positives.
- The job-candidate pool is not an evidence projection and must not be passed as `--projection`.
- Evaluation SHA-256: `6a7c16d2310bdc34f3fb4ee312f20b4c7b7631647be7b5b52bbb082d437509cb`.

Input SHA-256:

| Input | SHA-256 |
|---|---|
| `data/fitcv-p0-corpus/p0b/p0b_source_job_relevance_fixture_v2_human_frozen.json` | `6b9ab2cacd3bf72d4eec7ebb2c137c17b637a1c63ced606cd913241948e4a28c` |
| `data/fitcv-p0-corpus/p0b/p0b_source_job_review_packet_v2_human_adjudicated.json` | `48fc695e63988784925885895e00bef3279fed60990e6f8cec538e1c106fc8ac` |
| `data/fitcv-p0-corpus/p0b/p0b_source_job_source_group_map_v2.json` | `20e983a8c93eba3bfa0ff39756b0afdaa0f43ec4bfa0415931105e43f8d416a9` |
| `data/fitcv-p0-corpus/p0b/p0b_source_job_candidate_pool_v1.jsonl` | `2ba9e06d9479dafa1bf11e6a5455fc7c37ab1676b567661d26480412bc295cf0` |
| `data/fitcv-p0-corpus/p0b/p0b_source_job_evidence_link_review_v1.csv` | `aa8f3e28f0ef9d1f373e14479e3c759f3018d550e3bbd88c551e13eca6920a89` |
| `data/fitcv-p0-corpus/p0b/p0b_holdout_freeze_manifest_v1.json` | `9fec6b33e5c97c426190d0ad1922b466ee2e2484c496b6bfef78336e163a856e` |

## P1-B Evidence

- Source: `.tmp/p1b-approved-workload/evidence.json`.
- Run: `p1b-approved-sanitized-001`.
- Stored run: `succeeded`, checkpoint `completed`.
- Actions: `regenerate_once`, then `approve_as_is`.
- Accepted denominator: `1`.
- Final artifact: `012c8ce2-17a2-5a74-8eda-e0fe8c99cd82`.
- Projection schema: `accepted_cv_effort_v1`; regeneration count `1`; elapsed status `measured`.
- No efficiency claim beyond `n=1`.

## Verification

- `623 passed` for P1-B backend contract/app/worker/mirror suites.
- `79 passed, 1 deselected` for P0 public corpus and evidence regressions.
- `8 passed` for P0-B evaluator tests.
- `28 passed` for calibration benchmark tests.
- `156 passed` for responsibility, analysis, P0-B evaluator, benchmark, and holdout adapter regressions.
- `git diff --check` passed.
- Protected private/untracked paths were not staged or modified.

Remaining blocker: P0-B retrieval precision/recall remains below promotion thresholds; responsibility support truth is reconciled. P1-C and P2 remain deferred by approved scope.
