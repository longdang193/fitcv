with open('tests/test_enrich.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the last enrich_batch test and add our test after it
test_code = '''

def test_enrich_batch_calls_on_chunk_complete_for_each_chunk() -> None:
    """on_chunk_complete callback is invoked once per chunk with that chunk's results."""
    from unittest.mock import patch
    from fitcv.enrich import enrich_batch

    jobs = [{"job_url": f"u{i}"} for i in range(6)]
    chunk_calls: list[list[dict]] = []

    def on_chunk_complete(chunk_rows: list[dict]) -> None:
        chunk_calls.append(list(chunk_rows))

    with patch("fitcv.enrich.enrich_job", side_effect=_fake_enrich_job), \\
         patch("time.sleep"):
        result = enrich_batch(
            jobs,
            config={"enrichment_batch_size": 2, "enrichment_concurrency": 1},
            on_chunk_complete=on_chunk_complete,
        )

    # 6 jobs / batch_size 2 = 3 chunks
    assert len(chunk_calls) == 3
    # Each chunk should have 2 jobs
    assert all(len(chunk) == 2 for chunk in chunk_calls)
    # All jobs should be accounted for across chunks
    all_chunk_urls = [r["job_url"] for chunk in chunk_calls for r in chunk]
    assert sorted(all_chunk_urls) == [f"u{i}" for i in range(6)]
    # Final result should still match
    assert [r["job_url"] for r in result] == [f"u{i}" for i in range(6)]


def test_enrich_batch_on_chunk_complete_exception_does_not_propagate() -> None:
    """If on_chunk_complete raises, enrich_batch continues and returns results."""
    from unittest.mock import patch
    from fitcv.enrich import enrich_batch

    jobs = [{"job_url": f"u{i}"} for i in range(4)]

    def failing_callback(chunk_rows: list[dict]) -> None:
        raise RuntimeError("save failed")

    with patch("fitcv.enrich.enrich_job", side_effect=_fake_enrich_job), \\
         patch("time.sleep"):
        result = enrich_batch(
            jobs,
            config={"enrichment_batch_size": 2, "enrichment_concurrency": 1},
            on_chunk_complete=failing_callback,
        )

    # Should still return all results despite callback failures
    assert len(result) == 4
    assert [r["job_url"] for r in result] == [f"u{i}" for i in range(4)]
'''

# Insert before the last function or at the end
# Find a good insertion point - after test_enrich_batch_uses_configured_batch_size_and_concurrency
insert_marker = 'def test_enrich_batch_uses_configured_batch_size_and_concurrency'
if insert_marker in content:
    # Find the end of that function
    idx = content.find(insert_marker)
    # Find the next function definition or end of file
    next_def = content.find('\ndef test_', idx + len(insert_marker))
    if next_def == -1:
        # No more tests, append at end
        content = content.rstrip() + test_code + '\n'
    else:
        content = content[:next_def] + test_code + '\n' + content[next_def:]
else:
    # Append at end
    content = content.rstrip() + test_code + '\n'

with open('tests/test_enrich.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('OK')
