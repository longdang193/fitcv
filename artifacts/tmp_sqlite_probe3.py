import sqlite3, json
con=sqlite3.connect('data/fitcv_cp.sqlite3')
cur=con.cursor()
cur.execute("SELECT run_id,run_json,created_at FROM local_pipeline_runs ORDER BY created_at DESC LIMIT 8")
rows=cur.fetchall()
print('recent ids', [r[0] for r in rows])
run='c8d06315-c2c4-4fd3-b432-18dc15cbc9b5'
cur.execute("SELECT run_json FROM local_pipeline_runs WHERE run_id=?",(run,))
row=cur.fetchone(); print('run exists',bool(row))
if row:
    rj=json.loads(row[0])
    print('status',rj.get('status'),'finished',rj.get('finished_at'))
    rr = rj.get('run_result') or {}
    dbg = rr.get('cv_generation_debug_records') or []
    print('debug_records',len(dbg))
    for rec in dbg:
        if str(rec.get('status'))=='validation_failed':
            print('JOB',rec.get('job_url'))
            vf = rec.get('validation_final') or {}
            print('missing_sections',vf.get('missing_sections'))
            print('warnings',vf.get('warnings'))
            print('enabled_sections',rec.get('enabled_sections'))
            print('-----')
cur.execute("SELECT stage,level,message,payload_json FROM local_pipeline_run_events WHERE run_id=? ORDER BY created_at",(run,))
for s,l,m,pj in cur.fetchall():
    if 'validation' in s or 'validation failed' in m.lower():
        print('EV',s,l,m)
        if pj:
            p=json.loads(pj)
            print(' out',p.get('output_snapshot'))
con.close()
