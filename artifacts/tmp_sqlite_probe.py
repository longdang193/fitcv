import sqlite3, json, pathlib
p=pathlib.Path('data/fitcv_cp.sqlite3')
print('db exists',p.exists())
con=sqlite3.connect(p)
cur=con.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print('tables', [r[0] for r in cur.fetchall()])
for t in ['runs','run_events','events','pipeline_runs']:
    cur.execute(f"PRAGMA table_info({t})")
    cols=[c[1] for c in cur.fetchall()]
    if cols:
        print(t, cols)
cur.execute("SELECT run_id,status,created_at,finished_at FROM pipeline_runs ORDER BY created_at DESC LIMIT 5")
print('recent',cur.fetchall())
run='c8d06315-c2c4-4fd3-b432-18dc15cbc9b5'
cur.execute("SELECT run_id,status,error_message FROM pipeline_runs WHERE run_id=?",(run,))
print('run',cur.fetchone())
cur.execute("SELECT count(*) FROM run_events WHERE run_id=?",(run,))
print('event_count',cur.fetchone()[0])
cur.execute("SELECT stage,level,message,payload_json FROM run_events WHERE run_id=? ORDER BY created_at",(run,))
rows=cur.fetchall()
print('stages',sorted(set(r[0] for r in rows)))
for s,l,m,pj in rows:
    if 'validation' in s or 'validation failed' in m.lower():
        print('EV',s,l,m)
        if pj:
            p=json.loads(pj)
            print(' output_snapshot',p.get('output_snapshot'))
con.close()
