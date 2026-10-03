# FitCV Runtime Efficiency Baseline

- Evidence status: `canonical`
- Evidence schema: `fitcv.p1_ab.current_contract.v1`
- Source commit: `11732c6a72e6e816a19c0fc0e5efdae2fbd103e0`
- Fixture SHA-256: `74843e9fd3655d3c3a8f96a60fd98da3a6a78d6144b40289c8d83dcb17c8ceb5`
- Source fixture SHA-256: `4ba6f4b5459c805e2455e7912120e8cde6ffb7d274493c44613ac62ad053950d`
- Status: `complete`
- Persisted ordinary runs: `2`
- Accepted CVs: `13`
- Recorded accepted generation outcomes: `13`
- Attempted generation jobs: `23`
- Attempted outcome records: `23`
- Provider calls: `46`
- Tokens: `218203`
- Regenerations: `23`
- Render retries: `0`
- Unmatched traces: `0`
- Unattributed accepted artifacts: `0`
- Accepted-artifact cost per accepted CV: `{'provider_call_count': 2.0, 'token_total': 11041.076923076924, 'regeneration_count': 1.0, 'validation_failure_event_count': 1.0, 'validation_failure_count': 1.0, 'generation_elapsed_ms': 28956.0, 'elapsed_ms': 28956.0}`
- Total-workload cost per accepted CV: `{'provider_call_count': 3.5384615384615383, 'token_total': 16784.846153846152, 'regeneration_count': 1.7692307692307692, 'validation_failure_event_count': 0.0, 'generation_elapsed_ms': 42868.846153846156, 'end_to_end_wall_ms': 99474.58415384615}`
- First-pass acceptance rate: `0.0`
- Accepted final one-page: `{'count': 13, 'pass': 13, 'fail': 0, 'total': 13, 'rate': 1.0}`
- Retry success/failure: `13` / `10`
- Generation duration aggregate: `557295.0`
- Generation timing coverage: `{'measured': 23, 'unavailable': 0}`
- Artifact acceptance latency aggregate: `376428.0`
- Run wall-clock aggregate: `1293169.594`
- Measurement coverage: `{'attribution': {'measured': 13, 'unavailable': 0, 'total': 13, 'rate': 1.0, 'complete': True, 'matched': 13, 'unmatched': 0}, 'cost': {'measured': 13, 'unavailable': 0, 'total': 13, 'rate': 1.0, 'complete': True}, 'timing': {'measured': 23, 'unavailable': 0, 'total': 23, 'rate': 1.0, 'complete': True}, 'page_fit': {'measured': 13, 'unavailable': 0, 'total': 13, 'rate': 1.0, 'complete': True}, 'review_questions': {'measured': 13, 'unavailable': 0, 'total': 13, 'rate': 1.0, 'complete': True}, 'human_actions': {'measured': 13, 'unavailable': 0, 'total': 13, 'rate': 1.0, 'complete': True}, 'resolution_reuse': {'measured': 13, 'unavailable': 0, 'total': 13, 'rate': 1.0, 'complete': True}, 'page_fit_success': {'measured': 13, 'unavailable': 0, 'total': 13, 'rate': 1.0, 'complete': True}}`
- Optimization scorecard: `{'regeneration_causes': {'generation_format_defect': 13}, 'reuse_hits': {'status': 'measured', 'count': 0}, 'human_actions': {'status': 'measured', 'count': 0}, 'resolution_reuse': {'status': 'measured', 'count': 0}, 'proof_reuse': {'status': 'unavailable', 'measured': 0, 'reason': 'current trace contract does not persist this field'}, 'provider_calls_avoided': {'status': 'unavailable', 'measured': 0, 'reason': 'current trace contract does not persist this field'}, 'renders_avoided': {'status': 'unavailable', 'measured': 0, 'reason': 'current trace contract does not persist this field'}, 'tokens_avoided': {'status': 'unavailable', 'measured': 0, 'reason': 'current trace contract does not persist this field'}}`
- Run/job diversity: `{'run_count': 2, 'job_count': 23, 'job_type_count': 3, 'job_types': ['Full-time', 'Internship', 'Part-time']}`

Stage latency p50/p95 is reported from explicit stage samples; missing stages stay unavailable.
Generation duration, artifact acceptance latency, and run wall-clock time are separate metrics.
Accepted-artifact and total-workload per-CV metrics stay null unless attribution is complete.
