# FitCV Current Scorecard

- Evidence status: `unavailable`
- Unavailable reason: `fresh provider-backed local_first cohort produced no current-contract accepted records after uncertainty routing; P1-B measurement remains blocked`
- Evidence schema: `fitcv.p1_ab.current_contract.v1`
- Source commit: `7f29c76510b158667e731c0cfdb98411a8a76730`
- Fixture SHA-256: `56d06d363a0d393e19b1fc01c24db88136776bd18211bafdcbb5e04e8f8168b5`
- Source fixture SHA-256: `56d06d363a0d393e19b1fc01c24db88136776bd18211bafdcbb5e04e8f8168b5`
- Material metrics SHA-256: `cdf95798b93c12bce23e08845773d42af43578d0c142f364ac8924106e82ae72`
- Status: `incomplete`
- Persisted ordinary runs: `10`
- Accepted CVs: `0`
- Recorded accepted generation outcomes: `0`
- Attempted generation jobs: `10`
- Attempted outcome records: `10`
- Provider calls: `30`
- Tokens: `143904`
- Regenerations: `20`
- Gold effort digest source: `gold_cohort_effort`
- Render retries: `0`
- Unmatched traces: `0`
- Unattributed accepted artifacts: `0`
- Accepted-artifact cost per accepted CV: `None`
- Total-workload cost per accepted CV: `None`
- First-pass acceptance rate: `0.0`
- Accepted final one-page: `{'count': 0, 'pass': 0, 'fail': 0, 'total': 0, 'rate': 0.0}`
- Retry success/failure: `0` / `10`
- Generation duration aggregate: `310030.0`
- Generation timing coverage: `{'measured': 10, 'unavailable': 0}`
- Artifact acceptance latency aggregate: `0.0`
- Run wall-clock aggregate: `385709.929`
- Measurement coverage: `{'attribution': {'measured': 0, 'unavailable': 0, 'total': 0, 'rate': 0.0, 'complete': False, 'matched': 0, 'unmatched': 0}, 'cost': {'measured': 0, 'unavailable': 0, 'total': 0, 'rate': 0.0, 'complete': False}, 'timing': {'measured': 10, 'unavailable': 0, 'total': 10, 'rate': 1.0, 'complete': True}, 'page_fit': {'measured': 0, 'unavailable': 0, 'total': 0, 'rate': 0.0, 'complete': False}, 'review_questions': {'measured': 0, 'unavailable': 0, 'total': 0, 'rate': 0.0, 'complete': False}, 'human_actions': {'measured': 0, 'unavailable': 0, 'total': 0, 'rate': 0.0, 'complete': False}, 'resolution_reuse': {'measured': 0, 'unavailable': 0, 'total': 0, 'rate': 0.0, 'complete': False}, 'page_fit_success': {'measured': 0, 'unavailable': 0, 'total': 0, 'rate': 0.0, 'complete': False}}`
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
