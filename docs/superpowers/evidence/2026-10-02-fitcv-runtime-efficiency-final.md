# FitCV Runtime Efficiency Baseline

- Evidence status: `canonical`
- Status: `complete`
- Persisted ordinary runs: `2`
- Accepted CVs: `11`
- Recorded accepted generation outcomes: `11`
- Attempted generation jobs: `18`
- Provider calls: `33`
- Tokens: `144929`
- Regenerations: `15`
- Render retries: `0`
- Unmatched traces: `0`
- Unattributed accepted artifacts: `0`
- Accepted-artifact cost per accepted CV: `{'provider_call_count': 1.7272727272727273, 'token_total': 8387.363636363636, 'regeneration_count': 0.7272727272727273, 'validation_failure_count': 0.7272727272727273, 'generation_elapsed_ms': 24493.81818181818, 'elapsed_ms': 24493.81818181818}`
- Total-workload cost per accepted CV: `{'provider_call_count': 3.0, 'token_total': 13175.363636363636, 'regeneration_count': 1.3636363636363635, 'validation_failure_count': 0.6363636363636364, 'generation_elapsed_ms': 36942.545454545456, 'end_to_end_wall_ms': 103476.36272727273}`
- First-pass acceptance rate: `0.16666666666666666`
- Retry success/failure: `8` / `7`
- Generation duration aggregate: `406368.0`
- Generation timing coverage: `{'measured': 18, 'unavailable': 0}`
- Artifact acceptance latency aggregate: `269432.0`
- Run wall-clock aggregate: `1138239.99`
- Measurement coverage: `{'attribution': {'measured': 11, 'unavailable': 0, 'total': 11, 'rate': 1.0, 'complete': True, 'matched': 11, 'unmatched': 0}, 'cost': {'measured': 11, 'unavailable': 0, 'total': 11, 'rate': 1.0, 'complete': True}, 'timing': {'measured': 18, 'unavailable': 0, 'total': 18, 'rate': 1.0, 'complete': True}, 'page_fit': {'measured': 11, 'unavailable': 0, 'total': 11, 'rate': 1.0, 'complete': True}, 'review_questions': {'measured': 11, 'unavailable': 0, 'total': 11, 'rate': 1.0, 'complete': True}, 'human_actions': {'measured': 11, 'unavailable': 0, 'total': 11, 'rate': 1.0, 'complete': True}, 'resolution_reuse': {'measured': 11, 'unavailable': 0, 'total': 11, 'rate': 1.0, 'complete': True}}`
- Run/job diversity: `{'run_count': 2, 'job_count': 18, 'job_type_count': 3, 'job_types': ['Full-time', 'Internship', 'Part-time']}`

Generation duration, artifact acceptance latency, and run wall-clock time are separate metrics.
Accepted-artifact and total-workload per-CV metrics stay null unless attribution is complete.
