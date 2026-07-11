import sqlite3, json

db=r"C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\data\fitcv_cp.sqlite3"
ids=[
  '4d83ef03-4acc-4acd-8ea6-240127a21098',
  '5656eb4d-34ec-4445-938d-f49ebadb8e14',
  '84c1c6a2-4b5f-49d6-991c-b3197e94f1bb',
]
con=sqlite3.connect(db)
con.row_factory=sqlite3.Row
cur=con.cursor()

print('DB',db)
tables=[r[0] for r in cur.execute("select name from sqlite_master where type='table' order by name")]
print('tables',len(tables))
print('run tables',[t for t in tables if 'run' in t or 'event' in t])

for rid in ids:
    print('\n===',rid,'===')
    found=False
    for t in ['local_pipeline_runs','pipeline_runs','runs']:
        if t not in tables:
            continue
        try:
            row=cur.execute(f"select * from {t} where run_id=?",(rid,)).fetchone()
        except Exception:
            row=None
        if row:
            found=True
            print('found in',t,'status',row.get('status') if hasattr(row,'get') else row['status'])
            try:
                summary=row['summary_json']
                if summary:
                    s=json.loads(summary)
                    ts=s.get('trace_summary') or {}
                    print('trace keys', [k for k in sorted(ts.keys()) if any(x in k.lower() for x in ['rank','skip','reuse','fresh'])])
            except Exception as e:
                print('summary parse err',e)
    if not found:
        print('not found in run tables')
    if 'local_pipeline_run_events' in tables:
        ev=cur.execute("select stage, level, message, payload_json, created_at from local_pipeline_run_events where run_id=? order by created_at",(rid,)).fetchall()
        print('events',len(ev))
        for e in ev:
            txt=((e['message'] or '')+' '+(e['payload_json'] or '')).lower()
            if any(x in txt for x in ['ranking','skip','reuse','fresh','label_distribution']):
                print('-',e['created_at'],e['stage'],e['level'],(e['message'] or '')[:180])
