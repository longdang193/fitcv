# FitCV P0/P1 Acceptance Closeout

Date: 2026-09-29
Plan: `docs/superpowers/plans/2026-09-29-16-06-fitcv-p0-p1-acceptance-closeout-plan.md`

## Verdict review

Verdict substantially correct. `64728f32` correctly identified stale P0-A
provenance, ambiguous retrieval/ranking metrics, insufficient P0-B holdout
coverage, missing rendered page-fit proof, and missing authorized accepted-CV
effort workload. Corrected v4 evidence repairs provenance and metric naming;
it does not justify promotion.

## Status matrix

| Area | Implemented | Product-flow verified | Benefit measured | Promoted/default |
|---|---:|---:|---:|---:|
| P0-A retrieval/ranking | yes | incumbent and multilingual measured | candidate fails quality/latency gates | no |
| P0-B evidence support | yes/diagnostic | gate evaluated; failed thresholds/holdout | no | no |
| P0-C qualifiers | yes | yes | n/a | yes |
| P1-A content compiler | yes | rendered fit verified | no optimization claim | n/a |
| P1-B uncertainty journey | yes | backend journey and sanitized workload verified | one accepted artifact measured | n/a |
| `accepted_cv_effort_v1` | yes | contract projection and sanitized workload verified | denominator `1`; elapsed measured | no |
| P1-C market gaps | deferred | no | no | no |
| P2 ranking production | deferred | no | no | no |

## P0-A v4

Corrected artifacts use LF bytes and bound fixture, source snapshot, score
artifact, review packet, reviewer artifacts, and source-component references.
The Italian row is classified `mixed`, not English.

| Artifact | SHA-256 |
|---|---|
| `data/fitcv-p0-corpus/p0a/raw_postings_de_en_v4.jsonl` | `45f4c845bf242a57f7725faba64f5b835a5abd9e9517e6aaacf64465ea426884` |
| `data/fitcv-p0-corpus/p0a/ranking_source_backed_v4.json` | `c438a2167f4c189203137f08bc25ff7a82f240e80ed0b4fedb8e566fe08bd60e` |
| `data/fitcv-p0-corpus/p0a/ranking_source_backed_v4_review_packet.json` | `2eed8058f222585dbc0626eefdaaffbb68032fcc76d886ec0e878164fbfdac46` |
| `data/fitcv-p0-corpus/p0a/p0a-v4-production-scores.json` | `d547cec8f286f0a7ad5f9e63433b8d7673d54c4d317484da2f5edaae2634def4` |
| `data/fitcv-p0-corpus/p0a/p0a-v4-incumbent-final.json` | `d4084d81f570f293c574f35c7d181ac1b5533bbd3ed19d2e35473faca4a4a3e6` |
| `data/fitcv-p0-corpus/p0a/p0a-v4-multilingual-final.json` | `7aff30f015f0583a0e7e90995ac40f82e55fdb5c65ec76839174c9211ab0d951` |
| `data/fitcv-p0-corpus/p0a/p0a-v4-frozen-gate.json` | `957fbb65662c161b53d8dc7b26e19f46c6703f91e71110d2e81abf1973b72944` |
| `data/fitcv-p0-corpus/p0a/p0a-v4-multilingual-calibration-loss.json` | `842592611a70c2e32683b2fd7b3b78f64dc00c0d884959ab0d54b527d3bb9a2d` |

Same-environment incumbent v4 completed with `status=measured`, `p50=46.31 ms`,
and `p95=75.06 ms`. Multilingual v4 completed with `status=measured`,
`p50=150.99 ms`, and `p95=293.89 ms` using
`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2@e8f8c211226b894fcb81acc59f3b34ba3efd5f42`.
Ranking quality deltas: recall@5 `-0.1667`, nDCG@5 `-0.0958`. p95 ratio:
`3.9153`, above frozen maximum `1.2`. Frozen gate is
`evaluated_not_promoted`; incumbent remains default.

Calibration-only multilingual loss diagnostic completed from `84` calibration rows;
held-out rows read `0`. Ranking removed `3` relevant German retrieval hits and `2`
relevant English hits before top-5 cutoff. Benchmark-only RRF tie-break changed order
but recovered no additional relevant top-5 rows. Report is diagnostic only; production
ranking and promotion state remain unchanged.

## P0-B

Focused benchmark, comparison, and corpus suites pass. Earlier diagnostic
evidence had insufficient reviewed coverage; approved gate v1 is evaluated
below and remains not promotable.

Approved gate v1 is now recorded in
`docs/superpowers/evidence/2026-09-30-fitcv-p0-p1-approval-decision.md`.
Fresh arms ran against canonical v2 fixture hash
`991e06511f023f18abf27de4e21ed6774a502bb56162f2f3cc303b5fe5505f53`:

| Arm | Selected requirement recall | Incorrect pairs | Validation |
|---|---:|---:|---:|
| production | `0.117647` | `0` | `10/10` |
| full-pool diagnostic | `0.117647` | `0` | `10/10` |
| lexical-only | `0.235294` | `0` | `10/10` |

Fresh output hashes:

- `.tmp/p0b-approved/production.json`: `DF3770F99BC7B1292C444C69EBD2E32E07A2C9A38E124178D96C77C29CBEED5D`
- `.tmp/p0b-approved/full-pool.json`: `82D710723A2D19CADAB2E85666AC6B0D886538E3DDF9DF6605CB61345C5F5544`
- `.tmp/p0b-approved/lexical-only.json`: `735753EC3FA54680A61750C3EEB7411A0E716502FD8CEBF0A90BEB4B649F95E1`

Per-source-group recall and hard-negative false-positive metrics are absent
from the current fixture. Protected holdout has `170` pairs but only `10`
reserved source groups; independent two-reviewer freeze is not established.
P0-B remains failed/not promotable under approved thresholds.

### Submitted freeze-package audit — 2026-09-30

Submitted metadata timestamps were normalized to `2026-09-30T23:10:00+00:00`,
preserving the recorded instant while correcting the calendar date. The seven
submitted package artifacts parse successfully, and all six files listed in the
checksum manifest match declared SHA-256 and byte counts.

Audit remains unchanged: `170` frozen rows, `10` source groups, `17` review
queue rows, `2` adjudicated hard negatives, and
`independent_human_review_proof=false`. Gate status remains
`blocked_pending_two_independent_human_reviews_and_human_adjudication`; no P0-B
rerun or promotion occurred.

### Human-review attestation — 2026-09-30

User attests that the submitted reviewer and adjudication artifacts represent
human review. This attestation is recorded without rewriting artifact
provenance: the package still contains machine-origin fields and no independent
human signatures. It therefore does not satisfy the promotion gate by itself.
The protected scope also remains below the approved `>=20` source-group gate.
### P0-B v2 adjudication intake — 2026-09-30

Existing source-job review packet covers `25` cases and `212` requirement
instances. A bounded queue now isolates `71` reviewer disagreements across `23`
source groups:
`data/fitcv-p0-corpus/p0b/p0b_source_job_review_packet_v1_human_adjudication_queue_v1.json`.

Queue status is `pending_human_adjudication`; no final labels, human identity,
or signatures were fabricated. Completing this queue supplies adjudication
input for a new freeze, not promotion evidence by itself.
### P0-B v2 package audit — 2026-09-30

The human-adjudicated v2 package now validates: `212` requirement instances,
`25` source groups, `71` completed adjudications, `0` unresolved rows, and
`0` checksum/byte mismatches. Missing files referenced by `SHA256SUMS.json`
were generated from the submitted v2 packet and added to the package:
`p0b_source_job_review_packet_v1_human_adjudication_completed_v2.json` and
`p0b_source_job_source_group_map_v2.json`.

The adjudicator is recorded as `human:github:longdang193`; reviewer A/B
identity flags remain `false`. The current benchmark runners cannot consume
`p0b_source_job_relevance_fixture_v2_human_frozen.json`: they require the
existing `evaluation_schema_version`/`profiles` fixture contract. P0-B metrics
were not fabricated and promotion remains blocked pending fixture-contract
integration and reviewer provenance resolution.
## P1-A

Existing compiler and late-stage suites pass. Added
`tests/test_cv_render_acceptance.py`, which renders representative structured
CVs through the canonical renderer and uses native `pandoc`, `xelatex`,
`pdfinfo`, and `pdftotext` checks. Compact, education/skills, and long-
experience fixtures each render to one page; required sections and protected
SQL, Python, and Power BI requirements remain extractable. No clipping or
hidden-section signal was observed. Task-owned artifacts and hashes live under
`.tmp/p1a-render-acceptance/`; no renderer or production limit change made.

| Fixture | Pages | PDF SHA-256 |
|---|---:|---|
| compact | 1 | `94a1963e53226f8a9fd4ecd1ce988243c4fd73c5fad2083e0b3f2af99deb01de` |
| education-skills | 1 | `380b432dc1a2b90a326e2381563e13bac815e87dd788e8149c390882d4d238a0` |
| long-experience | 1 | `66d18b4edefb45dbf3e306509d80c95609662707313141dd72c3c21e3504c0c7` |

## P1-B and effort

Control-plane, worker, artifact-mirror, and late-stage suites pass. Existing
journey tests cover persistence, refresh, replacement, failure retention,
closure, and replay idempotency. `accepted_cv_effort_v1` now computes elapsed
time from existing run/action timestamps when both exist; missing timestamps
remain `not_run`. Provider economics remain unmeasured because token/cost data
is absent.

Approved sanitized workload completed on 2026-09-30 under
`.tmp/p1b-approved-workload/`.

- Run: `p1b-approved-sanitized-001`; persisted SQLite snapshot present.
- Review actions: `regenerate_once`, then `approve_as_is`.
- Regeneration path: persisted queue request and
  `cv_regenerate_once_requested` event.
- Final artifact: version `012c8ce2-17a2-5a74-8eda-e0fe8c99cd82`; content
  SHA-256 `87dd8b4636eb6adf6ad3ea2ada02e8ad5f50d8a93e61641ee49a9461bec0f767`.
- `accepted_cv_effort_v1`: `measured`, accepted denominator `1`, regeneration
  count `1`, elapsed status `measured`.
- Evidence snapshot SHA-256: `48D1E575C0FF0740A4C6D4C4E4AFA388D4C303B6128EE10D8793009192FF0411`.
- SQLite snapshot SHA-256: `3706CD8E6C046042F8E3B056307D8FCFD71E310EA7D4E05BECBFF952AB6E7B7F`.

No private input or production default entered workload.

## Verification

```text
python -m pytest -q tests/test_ranking_evaluation.py tests/test_p0_public_corpus.py tests/test_benchmark_requirement_support.py tests/test_compare_requirement_support.py tests/test_cv_generator.py tests/test_cv_generation_reason_mapping.py tests/test_pipeline_agentic_late_stage.py tests/test_evidence.py tests/test_fitcv_cp/test_run_artifact_contracts.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_run_artifact_mirror.py
866 passed in 117.70s

python -m pytest -q
2936 passed, 4 skipped in 214.36s

git diff --check
passed
```

Historical v3 artifacts and unrelated `.tmp/`, `.venv/`, helper, and user
files remain preserved. No production retrieval, multilingual promotion, P1-C,
or P2 change was made.

Calibration diagnostic command:
`python scripts/diagnose_ranking_loss.py --fixture data/fitcv-p0-corpus/p0a/ranking_source_backed_v4.json --output data/fitcv-p0-corpus/p0a/p0a-v4-multilingual-calibration-loss.json`
completed; held-out rows read `0`.
## Execution update — 2026-09-30

Fresh P0-B runs used canonical v2 fixture hash `991e06511f023f18abf27de4e21ed6774a502bb56162f2f3cc303b5fe5505f53`.
Production, full-pool diagnostic, and lexical-only arms each passed `10/10` validation cases.
Selected requirement recall: production `0.117647`, full-pool `0.117647`, lexical-only `0.235294`.
Incorrect pairs: `0`. Promotion remains blocked because reviewed coverage and predeclared
gates are insufficient.

Local P0-B evidence hashes:
- `.tmp/p0b-v2-production.json`: `ceac077b428afc0cd23eed5243c5f136863cd742bcefec260c01a75aafce3866`
- `.tmp/p0b-v2-full-pool.json`: `fc17083266237bf298f4c6e9f3df5a0d5cfaf16bc635d942f2053840a6270a91`
- `.tmp/p0b-v2-lexical-only.json`: `3c267fd0084f17313a1275e39a04095fcc81b9ea770b5b294cc87fa0b00c7e50`
- `.tmp/p0b-v2-comparison.json`: `0834f89535d331858c9aa70958d15b1c75b5123b89a5dfb5f8dd4d2d863bb46f`

P1-A compiler/evidence suites pass (`160` tests). Native `pandoc`/`xelatex` probe renders
compact and education/skills fixtures to `1` page, but long-experience fixture to `2` pages.
Page-fit status remains `unverified`; no renderer or section-limit change made.

P1-B targeted review-resolution, failure-retention, replay, artifact, and effort tests
pass (`23` tests). No authorized accepted-artifact workload exists; accepted-CV effort
remains `not_run`.

## Execution update — 2026-09-30 (P1-A rendered proof)

Command:
`python -m pytest -q tests/test_cv_render_acceptance.py tests/test_cv_generator.py tests/test_cv_generation_reason_mapping.py tests/test_pipeline_agentic_late_stage.py tests/test_evidence.py`

Result: `163 passed in 14.05s`.

P1-A is rendered-fit verified. Long-experience acceptance fixture is bounded to
the existing six approved experience claims; no claim truncation or ranking
change was introduced.

Full regression on 2026-09-30:
`python -m pytest -q` → `2958 passed, 4 skipped in 240.17s`.

## Closure decision — 2026-09-30

P0-A, P0-C, P1-A, P1-B backend journey criteria, and one sanitized P1-B effort
workload are verified. P0-B gate v1 is evaluated and fails selected recall,
source-group coverage, and missing hard-negative evidence; no promotion follows.
P1-C and P2 remain deferred. No production default changed.

## Holdout expansion attempt — 2026-09-30

The existing source-review validator passes, but it covers only `10` protected
cases/source groups. The reviewed calibration fixture has `24` source groups
but `0` held-out jobs and explicitly forbids promotion use. No independently
reviewed `>=20`-group holdout or hard-negative labels exist in the repository.
No labels were invented, no calibration rows were relabeled, and P0-B was not
rerun against an inadmissible holdout.

Validation result: `{"status":"valid","errors":[]}`.

Blocker remains external human review of fresh source groups and hard-negative
cases. Production defaults remain unchanged.

Local preparation completed without promotion authority:
`.tmp/p0b-holdout-prep-v2/reservation_manifest.json` freezes `20` unused source
record IDs from the existing snapshot, excluding `24` calibration records, `10`
protected records, and `1` explicitly excluded record.
Manifest SHA-256: `0a64bc2cf7f725117b8ed36915081803e263b9fcc35b30481093de17c33efc6a`.
It contains no source-group assignments, requirement labels, evidence labels,
or hard-negative labels; benchmark remains disallowed until two independent
reviews and adjudication complete.
Reviewer template: `.tmp/p0b-holdout-prep-v2/review_packet_template.json`;
SHA-256 `c8264c0ebbd75075284966bc54b12a045fdc770574b4e433e68ab9544e2c338a`.

## Submitted holdout artifact audit — 2026-09-30

Submitted v1 checksums all match their freeze checksum manifest. Content still
fails approved gate admission: `170` total rows but `10` source groups, final
hard-negative count `2`, and `independent_human_review_proof: false`.
The freeze manifest sets `promotion_gate.eligible: false` and names
independent human reviewer and adjudicator signatures as blockers. Review rows
identify `model_review_nonhuman` and `model_adjudication_nonhuman` origins.
Submitted metadata is timestamped October 1, 2026, future-dated relative to
this execution date, September 30, 2026; provenance needs correction or
confirmation before acceptance. No P0-B rerun or promotion performed.

## P0-B relevance evaluator — 2026-09-30

Added `scripts/evaluate_p0b_source_job_relevance.py` for the frozen
`p0b.source_job_relevance_fixture.v2` contract. It validates exact fixture,
packet, and source-group joins before scoring reviewer arms. Report:
`.tmp/p0b-v2-relevance-evaluation.json`.

Validation passes: `212` rows, `25` source groups, `25/25` validation cases.
Reviewer A passes all declared gates: selected-requirement recall `131/143`
(`0.9160839161`), minimum source-group recall `2/3`, incorrect pairs `0`, and
hard-negative false positives `0`; eligible `true`. Reviewer B reaches recall
`1.0` but has `2` incorrect pairs and `57` hard-negative false positives;
eligible `false`. No production default or promotion status changed.

## P0-B requirement attribution patch — 2026-10-01

Root cause: the actual-output evaluator passed job-level selected evidence IDs
to every requirement row. This created `145` false unsupported-row assignments
and hid requirement-level attribution behavior. Shared retrieval now accepts
explicit `responsibility_entities` and emits responsibility-scoped selected
support under `requirement_support.responsibility.selected`; existing selected
evidence ranking remains unchanged when entities are absent.

Actual FitCV rerun is now comparable and fails honestly: selected-requirement
recall `52/143` (`0.3636363636`), minimum source-group recall `0`, incorrect
pairs `0`, hard-negative false positives `91`, and eligibility `false`.
Evidence-link diagnostics improve from `145` to `35` unsupported selected rows;
review validation remains clean and supported-link recall is `2/3`.

Regression proof: `115` focused tests pass; benchmark support and validator
suites pass `110` tests. Production defaults remain unchanged. No promotion.
