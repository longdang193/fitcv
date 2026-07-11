import re

with open('src/fitcv/pipeline.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update _enrich_jobs_with_reuse signature to accept incremental save params
old_sig = '''def _enrich_jobs_with_reuse(
    normalized_jobs: list[dict[str, Any]],
    config: dict[str, Any],
    *,
    pipeline_store: PipelineStore | None = None,
    heartbeat_callback: Callable[[dict[str, Any]], None] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:'''

new_sig = '''def _enrich_jobs_with_reuse(
    normalized_jobs: list[dict[str, Any]],
    config: dict[str, Any],
    *,
    pipeline_store: PipelineStore | None = None,
    heartbeat_callback: Callable[[dict[str, Any]], None] | None = None,
    incremental_save_run_id: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:'''

assert old_sig in content, 'old_sig not found'
content = content.replace(old_sig, new_sig)

# 2. Find where enrich_batch is called and add the on_chunk_complete callback
# Need to find the exact enrich_batch call in the else branch (non-heartbeat path)
old_enrich_call = '''            fresh_rows = _run_enrich_call_with_polling(
                lambda: enrich_batch(
                    fresh_jobs,
                    config,
                    job_event_callback=_job_event_callback if emit_job_events_enabled else None,
                ),'''

new_enrich_call = '''            def _on_chunk_complete(chunk_rows: list[dict[str, Any]]) -> None:
                if not incremental_save_run_id or not pipeline_store:
                    return
                for row in chunk_rows:
                    job_url = extract_job_url(row)
                    if not job_url:
                        continue
                    row["raw_job_fingerprint"] = raw_job_fingerprints.get(job_url)
                    row["enrich_contract_fingerprint"] = enrich_contract_fingerprint
                    row["enrich_reuse_status"] = FRESH_ENRICHMENT_STATUS
                    row["reuse_decision"] = build_reuse_decision(
                        decision=FRESH_ENRICHMENT_STATUS,
                        reason_code="no_reusable_enrichment_row",
                        fingerprint=raw_job_fingerprints.get(job_url),
                        source_artifact_type="enrich",
                    )
                try:
                    pipeline_store.load_structured_jobs(chunk_rows, config)
                    pipeline_store.load_run_structured_jobs(chunk_rows, incremental_save_run_id, config)
                except Exception:
                    logger.warning("Incremental save failed for chunk", exc_info=True)

            fresh_rows = _run_enrich_call_with_polling(
                lambda: enrich_batch(
                    fresh_jobs,
                    config,
                    job_event_callback=_job_event_callback if emit_job_events_enabled else None,
                    on_chunk_complete=_on_chunk_complete if incremental_save_run_id else None,
                ),'''

assert old_enrich_call in content, 'old_enrich_call not found'
content = content.replace(old_enrich_call, new_enrich_call)

with open('src/fitcv/pipeline.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('OK')
