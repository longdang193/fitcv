import sqlite3, json

db = 'data/fitcv_cp.sqlite3'
ids = [
  '4d83ef03-4acc-4acd-8ea6-240127a21098',
  '5656eb4d-34ec-4445-938d-f49ebadb8e14',
  '84c1c6a2-4b5f-49d6-991c-b3197e94f1bb',
]
con = sqlite3.connect(db)
con.row_factory = sqlite3.Row
cur = con.cursor()

print('DB', db)
for rid in ids:
    row = cur.execute('select * from pipeline_runs where run_id=?', (rid,)).fetchone()
    print('\nRUN', rid, 'exists', bool(row))
    if not row:
        continue
    print('status', row['status'], 'created', row['created_at'], 'started', row['started_at'], 'completed', row['completed_at'])
    sj = row['summary_json']
    if not sj:
        print('summary_json none')
        continue
    s = json.loads(sj)
    tr = s.get('trace_summary') or {}
    keys = [k for k in tr.keys() if any(x in k.lower() for x in ('rank', 'reuse', 'skip', 'fresh'))]
    print('trace_keys', sorted(keys))
    for k in sorted(keys):
        print(' ', k, '=', tr[k])
