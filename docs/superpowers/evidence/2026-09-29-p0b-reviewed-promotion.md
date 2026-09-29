# P0-B Preparation and Diagnostic Evidence

Date: 2026-09-29. Base: `251ee0a2a7c3dbfba1404f5e620bc6383df965cb`.
Decision: **promotion_blocked**. Preparation and verified repairs are preservable;
human admission and final held-out evaluation remain incomplete.

## Corpus Audit and Repair

Current reviewed file contains 8 pairs, **5** unique requirements, 7 evidence
IDs, and 2 jobs. Manifest previously said 6 requirements. A regression derived
counts from exact rows, failed with `6 != 5`, then passed after the one-value fix.
Existing consumers are corpus tests; no corpus generator for this manifest was
found. Additional distinct evidence/pair count assertions guard the same drift.

Three relevance seed labels are marked approved, but neither rows nor manifest
establish two independent human judgments per case. Historical agent adjudication
does not satisfy the newly approved human gate. Relevance and qualified support
remain separate labels; `unknown` must not be converted to `unsupported`.

The current split has 6 German calibration pairs and 2 English held-out pairs.
Existing held-out cases have already been inspected in prior development and
cannot be presented as a newly untouched holdout. New held-out source groups must
be reserved before tuning, independently reviewed, and withheld from implementers.
Conservative CV source groups must stay in one split; filename numbering does
not establish translation identity.

## Unlabelled Calibration Review Packet

These six new candidate cases join existing public sources. They have **no
assigned relevance/support verdict, human reviewer identity, or approval**.
All are calibration-only preparation; they are not added to the admitted fixture.
The question column identifies a review topic, not an expected label.

Requirement source: `data/fitcv-p0-corpus/p0a/raw_postings_de_en.jsonl`, select
`source_id` and exact `description` span below. Original URLs are in
`source_job_url`. Evidence source:
`data/fitcv-p0-corpus/p0b/candidate_evidence_projection.jsonl`, select exact
`evidence_id`; retain `source_file`, `source_record_id`, `source_section`,
`profile_id`, `split_group_id`, and `pairing_status` from that row.

| Case ID | Job source ID | Exact requirement span | Evidence ID(s) | Review question |
| --- | --- | --- | --- | --- |
| cal-01 | 4103707442 | Du studierst im Bachelor oder Master in (interactive) medientechnologie- und marketingnahen Studiengängen. | ev_profile_002_de_cv_0024 | Does this evidence establish the education and field qualifiers? |
| cal-02 | 4160193650 | Du hast eine Leidenschaft für Datenanalyse und Unternehmensberatung | ev_profile_002_de_cv_0003 | Assess the full compound requirement against the profile paragraph. |
| cal-03 | 4160193650 | Verfügbarkeit: mindestens 6+ Monate für ein reguläres Praktikum oder ein Masterarbeit-Praktikum, mit der Möglichkeit, anschließend für eine Vollzeitstelle in Betracht gezogen zu werden | ev_profile_001_en_cv_0004 | Assess duration and future availability separately. |
| cal-04 | 4160193650 | Sprichst fließend Englisch; Deutschkenntnisse sind ein Plus | ev_profile_002_de_cv_0030 | Separate required language fluency from optional language knowledge. |
| cal-05 | 4472052252 | As this internship is located in Germany within an international working context, we are looking for fluency in German and English. | ev_profile_002_en_cv_0010 | Assess each language qualifier against the technical-skills row. |
| cal-06 | 4160193650 | Du hast eine Leidenschaft für Datenanalyse und Unternehmensberatung | ev_profile_002_de_cv_0003; ev_profile_002_de_cv_0006 | Assess individual evidence pairs and their combined contribution. |

Per case, each human independently records: real reviewer ID, timestamp, exact
requirement span/offset, evidence IDs, relevance label, qualified-support verdict,
each qualifier verdict, rationale, and source references. An adjudicator resolves
disagreement before the lead admits the case. Record both original judgments;
do not replace them with a single unexplained final label.

Remaining coverage: selection misses need actual retrieval/selection traces;
aliases, explicit negation, production/context qualifiers, and balanced positive,
negative, ambiguous examples still need approved source-backed cases. The packet
does not establish any category as covered before human review. No new held-out
examples were selected or tuned. No minimum sample size is invented here.

An agent-proposed case from job `4470112984` was excluded: its suggested English
duration anchor was not established by the inspected text. The snapshot marks
that row `en` although the description is Italian. That pre-existing P0-A
admission issue requires corpus-owner re-admission and new hashes before using
it for language-stratified P0-B claims; this packet does not consume that row.

## Acceptance Decisions Required Before Tuning

- Baseline: proposed incumbent `production` on the same future admitted held-out
  fixture. The synthetic diagnostic baseline below is not the promotion baseline.
- Owner must approve recall non-inferiority margins, sample-size/uncertainty rule,
  split/source-group policy, latency limit and workload, and cost measurement/limit.
- Both recalls must improve or meet those approved margins; observed false-qualified
  pairs and qualifier leakage must be zero. Zero observed errors is sample evidence,
  not proof of zero population risk.
- Coverage and exact source provenance must pass, with two human judgments and
  resolved disagreements per case. Offline token estimates cannot establish provider cost.

## Fresh Diagnostic Runs

The CLI consumes `tests/fixtures/requirement_support_benchmark.json` and has no
reviewed-corpus or held-out selector. It benchmarks 16 synthetic scenarios with
17 validation cases; all three arms passed 17/17 using 5 warmups and 50 runs.
This demonstrates those regression cases only, not general harness correctness
or production coverage. The `full_pool_diagnostic` arm is a diagnostic upper-bound
comparison, not an automatically eligible production replacement.

| Arm | Median total ms | Reported total p95 ms | Output |
| --- | ---: | ---: | --- |
| production | 2.2473 | 10.8012 | .tmp/p0b-20260929-010143-production.json |
| full_pool_diagnostic | 2.9747 | 10.6068 | .tmp/p0b-20260929-010143-full_pool_diagnostic.json |
| lexical_only | 1.8013 | 8.2233 | .tmp/p0b-20260929-010143-lexical_only.json |

Timing aggregation is median of per-scenario medians and maximum of per-scenario
p95 values. It is not a pooled workload percentile or a before/after speedup claim.
No provider calls were made. Producer code and policy were unchanged during runs;
comparison code was subsequently repaired and is identified by byte hash below.

Commands (run each arm separately, using the corresponding unique output above):

```powershell
py -3.13 scripts/benchmark_requirement_support.py --arm production --runs 50 --warmups 5 --output .tmp/p0b-20260929-010143-production.json
py -3.13 scripts/benchmark_requirement_support.py --arm full_pool_diagnostic --runs 50 --warmups 5 --output .tmp/p0b-20260929-010143-full_pool_diagnostic.json
py -3.13 scripts/benchmark_requirement_support.py --arm lexical_only --runs 50 --warmups 5 --output .tmp/p0b-20260929-010143-lexical_only.json
py -3.13 scripts/compare_requirement_support.py --inputs .tmp/p0b-20260929-010143-production.json,.tmp/p0b-20260929-010143-full_pool_diagnostic.json,.tmp/p0b-20260929-010143-lexical_only.json --output .tmp/p0b-20260929-010143-comparison-final.json
```

## Provenance

SHA-256 of exact bytes:

| Artifact | SHA-256 |
| --- | --- |
| Synthetic fixture | 58acd4396905dc6b5b1c33c50b91c5eebc27c49db1abf35fb14dd20854bc977b |
| Benchmark script | de9035f73c19dc40d87376d9068c5be858ae34a3020309e366fe5e5a77d1159b |
| config/policy/cv_analysis.yaml | 3630144170991755df78a62a308e9d56cd182fa726bfb7edbdfd16e25b7d81ae |
| Reviewed rows | e4ffc9ade4fa8834b8f7052d0577fbc9d3fb04e02be28d250ad34ae8a1efbdcb |
| Corrected reviewed manifest | c1300edbabdc527eb9089116e3aed643c431a9331d436f06a103d746933e74ba |
| Evidence projection | 376387c05085b36a76e869f8a4632efa5ffd12175f8c137cee9213c826456e68 |
| Projection manifest | 9089c1335c7e6d98e99288d8b4377849a015a8065857987cd658c04fb3889154 |
| Admitted P0-A job snapshot | 8c989136bd672841862db99e1bde5f02ec0dc121ce1555b202b04db7edfcc0fd |
| Final comparison script | fb72e116ee533a339243022bbc898f67a0ffcfffcb475eea12d15c550b24175e |
| Production report | e157916fb92f002d751be3513b1f4290b2e00e2582eda4dfb6e84ad3399c38bf |
| Full-pool diagnostic report | d90c55b04905f804eeca7646cda9623673c5236a2ca7e06077b5274b18a2604e |
| Lexical-only report | 07a0bf48c48f0b6ae51ea67bef4c3b2ac61f2eb96f5911082e70d0d6f23e4ad4 |
| Generated final comparison | ad7ba6b0e0a65a2e7b5e891c713c55b15e9c3452cc3fd3b36bedca2bc0802762 |
| Archived LF comparison | 3e8a7ab435caa0ec09609cb50ecefbf0bc7f724f0c6b8532715b9dfe29ba3c9a |

Archived comparison: `docs/superpowers/evidence/2026-09-29-p0b-comparison.json`.
Parsed JSON equality with the generated final report passed; LF normalization
explains the differing byte hash. Raw arm reports remain in the local `.tmp/`
paths above. All three arms have selected qualified-requirement recall 1.0,
selected evidence-pair recall 1.0, and zero observed incorrect pairs on this
synthetic fixture. The comparison preserves all three arms.

## Confirmed Comparison Defects

`run_inputs` filtered the canonical arm map to two entries, silently discarding
`lexical_only`. The legacy `current/full-pool` branch had the same loss. Both now
retain every supplied arm. Duplicate arm keys previously overwrote inputs;
missing/duplicate arm identities now fail validation.

Shared comparison expressions used `or 0.0` and absent `incorrect_pairs` became
an empty list. Missing measurements could therefore produce true non-decreasing
recall and zero false-qualified pairs. Current comparisons now require explicit
pair lists and finite numeric recall in [0, 1], rejecting booleans. Shared fixture
validation rejects blank hashes, including whitespace-only hashes.

## Verification and Review

Corpus count regression: initial `1 failed, 4 passed`; after repair `5 passed`.
Benchmark lane reported its red phase as `8 failed, 5 passed` for invalid recall,
hash, and missing-pair inputs. Lead's final extension reproduced whitespace hashes
and legacy arm loss as `2 failed, 1 passed`; after repair, combined focused command:

`py -3.13 -m pytest -q tests/test_compare_requirement_support.py tests/test_benchmark_requirement_support.py tests/test_p0_public_corpus.py`

Result: **45 passed**. All fresh benchmark/comparison commands exited 0.

Two independent technical reviews completed: `review-1` PASS for source joins,
packet, human gates and manifest counts; `review-2` PASS for benchmark code/tests
and producer compatibility. Subsequent lead changes normalize blank hashes and
retain legacy arms, with the focused red/green proof above; no third review was
requested. Technical reviews do not supply required human labels.

Shared planning validators reported historical errors outside this change.
After fixing the new plan's field formatting and dependency syntax, neither
validator reports a finding for this plan. Repository-wide validation is not
claimed green. Final staged whitespace and preservation checks are recorded in
the plan before commit.
