import sqlite3
con=sqlite3.connect(r"runtime/fitcv_cp.sqlite3")
con.row_factory=sqlite3.Row
cur=con.cursor()
rows=cur.execute("select run_id,status,created_at,started_at,completed_at,total_jobs,passed_filter,ranked,cvs_generated from local_pipeline_runs order by datetime(created_at) desc limit 25").fetchall()
print('recent runs',len(rows))
for r in rows:
    print(r['created_at'], r['run_id'], 'status='+str(r['status']), 'total='+str(r['total_jobs']), 'passed='+str(r['passed_filter']), 'ranked='+str(r['ranked']), 'cv='+str(r['cvs_generated']))
