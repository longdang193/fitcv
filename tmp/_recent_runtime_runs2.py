import sqlite3, json
con=sqlite3.connect(r"runtime/fitcv_cp.sqlite3")
con.row_factory=sqlite3.Row
cur=con.cursor()
rows=cur.execute("select run_id, created_at, run_json from local_pipeline_runs order by datetime(created_at) desc limit 30").fetchall()
print('recent runs',len(rows))
for r in rows:
    payload={}
    try:
      payload=json.loads(r['run_json'] or '{}')
    except Exception:
      pass
    print(r['created_at'], r['run_id'], 'status='+str(payload.get('status')), 'ranked='+str(payload.get('ranked')), 'passed='+str(payload.get('passed_filter')), 'total='+str(payload.get('total_jobs')))
