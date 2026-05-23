import sqlite3, json
con=sqlite3.connect('data/fitcv_cp.sqlite3')
cur=con.cursor()
for t in ['local_pipeline_runs','local_pipeline_run_events']:
    cur.execute(f"PRAGMA table_info({t})")
    print(t,[c[1] for c in cur.fetchall()])
cur.execute("SELECT run_id,status,created_at,finished_at FROM local_pipeline_runs ORDER BY created_at DESC LIMIT 8")
print('recent',cur.fetchall())
run='c8d06315-c2c4-4fd3-b432-18dc15cbc9b5'
cur.execute("SELECT run_id,status,error_message,run_result_json FROM local_pipeline_runs WHERE run_id=?",(run,))
row=cur.fetchone(); print('run exists',bool(row))
if row:
    print('status',row[1],'error',row[2])
    rr = json.loads(row[3]) if row[3] else {}
    dbg = rr.get('cv_generation_debug_records') or []
    print('debug_records',len(dbg))
    for rec in dbg:
        if str(rec.get('status'))=='validation_failed':
            print('JOB',rec.get('job_url'))
            print('warnings',rec.get('validation_final',{}).get('warnings'))
            print('missing',rec.get('validation_final',{}).get('missing_sections'))
            print('---')
cur.execute("SELECT count(*) FROM local_pipeline_run_events WHERE run_id=?",(run,))
print('event_count',cur.fetchone()[0])
cur.execute("SELECT stage,level,message,payload_json FROM local_pipeline_run_events WHERE run_id=? ORDER BY created_at",(run,))
for s,l,m,pj in cur.fetchall():
    if 'validation' in s or 'validation failed' in m.lower():
        print('EV',s,l,m)
        if pj:
            p=json.loads(pj)
            print(' out',p.get('output_snapshot'))
con.close()
