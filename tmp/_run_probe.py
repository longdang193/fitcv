import sqlite3, json
con=sqlite3.connect('data/fitcv_cp.sqlite3')
con.row_factory=sqlite3.Row
cur=con.cursor()
ids=['4d83ef03-4acc-4acd-8ea6-240127a21098','5656eb4d-34ec-4445-938d-f49ebadb8e14','84c1c6a2-4b5f-49d6-991c-b3197e94f1bb']
print('tables with run', [r[0] for r in cur.execute("select name from sqlite_master where type='table' and name like '%run%'")])
for rid in ids:
    row=cur.execute('select * from local_pipeline_runs where run_id=?',(rid,)).fetchone()
    print('\nRUN',rid,'found',bool(row))
    if not row: 
        continue
    print(' status=',row['status'],'created=',row['created_at'],'started=',row['started_at'],'completed=',row['completed_at'])
    summary=row['summary_json']
    if summary:
      s=json.loads(summary)
      ts=s.get('trace_summary') or {}
      for k in sorted(ts):
        if any(x in k.lower() for x in ['rank','reuse','skip','fresh']):
          print('  ',k,'=',ts[k])
    ev=list(cur.execute('select stage, level, message, payload_json, created_at from local_pipeline_run_events where run_id=? order by created_at',(rid,)))
    print(' events=',len(ev))
    for e in ev:
      msg=(e['message'] or '')
      pl=(e['payload_json'] or '')
      if any(tok in (msg+pl).lower() for tok in ['ranking','skip','reus','fresh','cache']):
        print('  -',e['created_at'],e['stage'],e['level'],msg)
