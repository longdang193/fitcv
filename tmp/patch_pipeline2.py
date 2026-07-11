with open('src/fitcv/pipeline.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Update the call to _enrich_jobs_with_reuse to pass incremental_save_run_id
old_call = '''                enriched, fresh_enriched_rows = _enrich_jobs_with_reuse(
                    surviving_normalized,
                    enrich_runtime_config,
                    pipeline_store=pipeline_store,
                    heartbeat_callback=('''

new_call = '''                enriched, fresh_enriched_rows = _enrich_jobs_with_reuse(
                    surviving_normalized,
                    enrich_runtime_config,
                    pipeline_store=pipeline_store,
                    incremental_save_run_id=run_id,
                    heartbeat_callback=('''

assert old_call in content, 'old_call not found'
content = content.replace(old_call, new_call)

with open('src/fitcv/pipeline.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('OK')
