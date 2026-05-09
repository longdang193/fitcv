---
layer: change
artifact_type: spec
status: proposed
parent_thread: workstream-pipeline-efficiency-and-reuse.efficiency-reuse-exact-match-contract
---

# Pipeline Efficiency Exact Match Contract Bootstrap Spec

## Goal

Establish parent-thread linkage so pipeline-efficiency workstream lifecycle can be validated while detailed implementation specs are refined.

## Scope

- define exact-match reuse contract boundaries for deterministic stage reuse
- identify required evidence fields for cache eligibility and invalidation
- reserve compatibility constraints for downstream implementation plans

## Step 1 Confirmed Contract

Current exact-match reuse is stage-owned and payload-based:

- shortlist query reuse: deterministic candidate-query components -> `candidate_query_signature`
- shortlist contract invalidation: `candidate_query_contract_fingerprint`
- reranker reuse: job URL + rendered scoring prompt + ranking contract fingerprint -> `ai_score_input_fingerprint`
- `cv_analysis` reuse: normalized candidate profile payload + normalized job-context payload + `cv_analysis` contract fingerprint -> `analysis_input_fingerprint`

Confirmed hash strategy:

- each stage canonicalizes bounded JSON payloads
- each stage computes SHA-256 over stable JSON serialization
- contract fingerprints separate behavior/config drift from payload drift
- exact-match eligibility requires both payload fingerprint match and contract fingerprint match for owning stage

## Step 2 Invalidation And Persistence Requirements

Invalidation triggers confirmed from current source:

- shortlist embedding reuse invalidates when `candidate_query_signature` changes or `candidate_query_contract_fingerprint` changes
- shortlist lookup is latest-row-wins by `created_at`; stale rows may remain stored but are not eligible when signature or contract drift
- reranker reuse invalidates when rendered prompt changes, `job_url` changes, or ranking contract fingerprint changes
- `cv_analysis` reuse invalidates when normalized profile payload changes, normalized job-context payload changes, or `cv_analysis` contract fingerprint changes
- jobs blocked before analysis by reranker fit are not candidates for reusable `cv_analysis` rows because analysis never executes

Persistence requirements for exact-match reuse:

- shortlist stage must persist: `candidate_query_signature`, `candidate_query_contract_fingerprint`, canonical component payload JSON, query text, embedding payload, and write timestamp
- ranking stage reusable record must carry: `job_url`, `ai_score_input_fingerprint`, reused row payload, and explicit reuse status
- `cv_analysis` reusable record must carry: `job_url`, `analysis_input_fingerprint`, status, decision-chain fields, evidence payload, evidence-used summary, gap summary, fit classification, and failure payloads when present
- evidence-selection table by itself is not sufficient for `cv_analysis` exact-match reuse because current reuse path expects full analysis-record snapshots, not only selected evidence rows
- exact-match rollout therefore needs persisted reusable snapshot surfaces for ranking and `cv_analysis`, or an equivalent materialized store that can reconstruct those rows losslessly
