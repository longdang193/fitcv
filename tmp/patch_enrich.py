import re

with open('src/fitcv/enrich.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add on_chunk_complete parameter to signature
old_sig = '''def enrich_batch(
    normalized_jobs: list[dict[str, Any]],
    config: dict[str, Any],
    *,
    job_event_callback: Callable[[dict[str, Any]], None] | None = None,
) -> list[dict[str, Any]]:'''

new_sig = '''def enrich_batch(
    normalized_jobs: list[dict[str, Any]],
    config: dict[str, Any],
    *,
    job_event_callback: Callable[[dict[str, Any]], None] | None = None,
    on_chunk_complete: Callable[[list[dict[str, Any]]], None] | None = None,
) -> list[dict[str, Any]]:'''

assert old_sig in content, 'old_sig not found'
content = content.replace(old_sig, new_sig)

# 2. Update docstring
old_doc_tail = '''    Rate limiting: request-start pacing is shared across chunk workers using a
    global slot scheduler. This preserves global throttling while allowing
    overlapping in-flight API calls when latency exceeds pacing interval.
    \"\"\"'''

new_doc_tail = '''    Rate limiting: request-start pacing is shared across chunk workers using a
    global slot scheduler. This preserves global throttling while allowing
    overlapping in-flight API calls when latency exceeds pacing interval.

    Incremental persistence: if on_chunk_complete is provided, it is called with
    each chunk's results immediately after that chunk finishes (in completion
    order). This allows callers to persist partial results incrementally rather
    than waiting for the entire batch to complete.
    \"\"\"'''

assert old_doc_tail in content, 'old_doc_tail not found'
content = content.replace(old_doc_tail, new_doc_tail)

# 3. Add on_chunk_complete call after each future.result()
old_collect = '''        chunk_results: list[list[dict[str, Any]]] = [None] * len(futures)  # type: ignore[list-item]
        for idx, future in enumerate(futures):
            # Calling .result() re-raises any exception from the chunk.
            # This preserves fail-fast semantics: if any chunk raises a
            # non-recoverable exception, it propagates here immediately.
            chunk_results[idx] = future.result()'''

new_collect = '''        chunk_results: list[list[dict[str, Any]]] = [None] * len(futures)  # type: ignore[list-item]
        for idx, future in enumerate(futures):
            # Calling .result() re-raises any exception from the chunk.
            # This preserves fail-fast semantics: if any chunk raises a
            # non-recoverable exception, it propagates here immediately.
            chunk_results[idx] = future.result()
            if on_chunk_complete is not None and chunk_results[idx]:
                try:
                    on_chunk_complete(chunk_results[idx])
                except Exception:
                    logger.warning('on_chunk_complete callback failed for chunk %d', idx, exc_info=True)'''

assert old_collect in content, 'old_collect not found'
content = content.replace(old_collect, new_collect)

with open('src/fitcv/enrich.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('OK')
