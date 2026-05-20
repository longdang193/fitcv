import json
run='b5acf9de-7475-43b8-a44f-caf5d7597cc9'
d=json.load(open(f'tmp/{run}-settings-used.json',encoding='utf-8'))
e=d['effective_settings']
print('stage_runtime.enrich.concurrency', e['stage_runtime']['enrich']['concurrency'])
print('stage_runtime.enrich.sleep_secs', e['stage_runtime']['enrich']['sleep_secs'])
print('stage_runtime.enrich.batch_size', e['stage_runtime']['enrich']['batch_size'])
print('stage_runtime.ranking.sleep_secs', e['stage_runtime']['ranking']['sleep_secs'])
print('stage_runtime.ranking.concurrency', e['stage_runtime']['ranking']['concurrency'])
print('stage_runtime.cv_analysis.concurrency', e['stage_runtime']['cv_analysis']['concurrency'])
print('stage_runtime.cv_generation.concurrency', e['stage_runtime']['cv_generation']['concurrency'])
sm=e['synonym_management']
print('synonym.apply_to_run_enabled', sm['apply_to_run_enabled'])
print('synonym.promote_global_enabled', sm['promote_global_enabled'])
