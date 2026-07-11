with open('tests/test_pipeline.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Update the assertion to include on_chunk_complete=None
old_assert = '''mock_enrich_batch.assert_called_once_with([jobs[1]], {"gemini_model": "gemini-2.5-flash"}, job_event_callback=None)'''
new_assert = '''mock_enrich_batch.assert_called_once_with([jobs[1]], {"gemini_model": "gemini-2.5-flash"}, job_event_callback=None, on_chunk_complete=None)'''

assert old_assert in content, 'old_assert not found'
content = content.replace(old_assert, new_assert)

with open('tests/test_pipeline.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('OK')
