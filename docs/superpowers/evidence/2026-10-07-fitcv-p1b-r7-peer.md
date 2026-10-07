# FitCV Current Scorecard

- Evidence status: `canonical`
- Evidence schema: `fitcv.p1_ab.current_contract.v1`
- Source commit: `1d11fe5b32e806ac1bb4d93ab80adbdc4de39c52`
- Fixture SHA-256: `56d06d363a0d393e19b1fc01c24db88136776bd18211bafdcbb5e04e8f8168b5`
- Source fixture SHA-256: `56d06d363a0d393e19b1fc01c24db88136776bd18211bafdcbb5e04e8f8168b5`
- Material metrics SHA-256: `a0a38beea68ff6d1815e68336d15d6f553510ae222048e4056a1b937c9f39769`
- Status: `complete`
- Persisted ordinary runs: `10`
- Accepted CVs: `10`
- Recorded accepted generation outcomes: `10`
- Attempted generation jobs: `10`
- Attempted outcome records: `10`
- Provider calls: `10`
- Tokens: `47586`
- Regenerations: `0`
- Gold effort digest source: `gold_cohort_effort`
- Render retries: `0`
- Unmatched traces: `0`
- Unattributed accepted artifacts: `0`
- Accepted-artifact cost per accepted CV: `{'provider_call_count': 1.0, 'token_total': 4758.6, 'regeneration_count': 0.0, 'validation_failure_event_count': 0.0, 'validation_failure_count': 0.0, 'generation_elapsed_ms': 10884.4, 'elapsed_ms': 10884.4}`
- Total-workload cost per accepted CV: `{'provider_call_count': 1.0, 'token_total': 4758.6, 'regeneration_count': 0.0, 'validation_failure_event_count': 0.0, 'generation_elapsed_ms': 10884.4, 'end_to_end_wall_ms': 22705.6175}`
- First-pass acceptance rate: `1.0`
- Accepted final one-page: `{'count': 10, 'pass': 10, 'fail': 0, 'total': 10, 'rate': 1.0}`
- Retry success/failure: `0` / `0`
- Generation duration aggregate: `108844.0`
- Generation timing coverage: `{'measured': 10, 'unavailable': 0}`
- Artifact acceptance latency aggregate: `108844.0`
- Run wall-clock aggregate: `227056.175`
- Measurement coverage: `{'attribution': {'measured': 10, 'unavailable': 0, 'total': 10, 'rate': 1.0, 'complete': True, 'matched': 10, 'unmatched': 0}, 'cost': {'measured': 10, 'unavailable': 0, 'total': 10, 'rate': 1.0, 'complete': True}, 'timing': {'measured': 10, 'unavailable': 0, 'total': 10, 'rate': 1.0, 'complete': True}, 'page_fit': {'measured': 10, 'unavailable': 0, 'total': 10, 'rate': 1.0, 'complete': True}, 'review_questions': {'measured': 10, 'unavailable': 0, 'total': 10, 'rate': 1.0, 'complete': True}, 'human_actions': {'measured': 10, 'unavailable': 0, 'total': 10, 'rate': 1.0, 'complete': True}, 'resolution_reuse': {'measured': 10, 'unavailable': 0, 'total': 10, 'rate': 1.0, 'complete': True}, 'page_fit_success': {'measured': 10, 'unavailable': 0, 'total': 10, 'rate': 1.0, 'complete': True}}`
- Optimization scorecard: `{'regeneration_causes': {}, 'reuse_hits': {'status': 'measured', 'count': 0}, 'human_actions': {'status': 'measured', 'count': 0}, 'resolution_reuse': {'status': 'measured', 'count': 0}, 'sections': {'CORRECTNESS': {'status': 'measured', 'failure_categories': {}, 'denominator': 'accepted_cv_records'}, 'PRODUCT PARITY': {'status': 'measured', 'resolution_reuse': {'status': 'measured', 'count': 0}, 'denominator': 'accepted_cv_records'}, 'EFFICIENCY': {'status': 'measured', 'provider_calls': {'status': 'measured', 'denominator': 'accepted_cv_records'}, 'savings': {'proof_reuse': {'status': 'unavailable', 'measured': 0, 'reason': 'current trace contract does not persist this field'}, 'provider_calls_avoided': {'status': 'unavailable', 'measured': 0, 'reason': 'current trace contract does not persist this field'}, 'renders_avoided': {'status': 'unavailable', 'measured': 0, 'reason': 'current trace contract does not persist this field'}, 'tokens_avoided': {'status': 'unavailable', 'measured': 0, 'reason': 'current trace contract does not persist this field'}}}, 'HUMAN EFFORT': {'status': 'measured', 'human_actions': {'status': 'measured', 'count': 0, 'denominator': 'accepted_cv_records'}, 'review_time_ms': {'status': 'unavailable', 'reason': 'trace contract does not persist review duration'}}}, 'proof_reuse': {'status': 'unavailable', 'measured': 0, 'reason': 'current trace contract does not persist this field'}, 'provider_calls_avoided': {'status': 'unavailable', 'measured': 0, 'reason': 'current trace contract does not persist this field'}, 'renders_avoided': {'status': 'unavailable', 'measured': 0, 'reason': 'current trace contract does not persist this field'}, 'tokens_avoided': {'status': 'unavailable', 'measured': 0, 'reason': 'current trace contract does not persist this field'}}`
- Run/job diversity: `{'run_count': 10, 'job_count': 10, 'job_type_count': 2, 'job_types': ['Contract', 'Part-time']}`

Stage latency p50/p95 is reported from explicit stage samples; missing stages stay unavailable.
Generation duration, artifact acceptance latency, and run wall-clock time are separate metrics.
Accepted-artifact and total-workload per-CV metrics stay null unless attribution is complete.

## CORRECTNESS
- `{'status': 'measured', 'failure_categories': {}, 'denominator': 'accepted_cv_records'}`

## PRODUCT PARITY
- `{'status': 'measured', 'resolution_reuse': {'status': 'measured', 'count': 0}, 'denominator': 'accepted_cv_records'}`

## EFFICIENCY
- `{'status': 'measured', 'provider_calls': {'status': 'measured', 'denominator': 'accepted_cv_records'}, 'savings': {'proof_reuse': {'status': 'unavailable', 'measured': 0, 'reason': 'current trace contract does not persist this field'}, 'provider_calls_avoided': {'status': 'unavailable', 'measured': 0, 'reason': 'current trace contract does not persist this field'}, 'renders_avoided': {'status': 'unavailable', 'measured': 0, 'reason': 'current trace contract does not persist this field'}, 'tokens_avoided': {'status': 'unavailable', 'measured': 0, 'reason': 'current trace contract does not persist this field'}}}`

## HUMAN EFFORT
- `{'status': 'measured', 'human_actions': {'status': 'measured', 'count': 0, 'denominator': 'accepted_cv_records'}, 'review_time_ms': {'status': 'unavailable', 'reason': 'trace contract does not persist review duration'}}`
