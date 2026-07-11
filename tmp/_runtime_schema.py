import sqlite3
con=sqlite3.connect(r"runtime/fitcv_cp.sqlite3")
cur=con.cursor()
for t in ['local_pipeline_runs','local_pipeline_run_events']:
    print('\nTABLE',t)
    cols=cur.execute(f"pragma table_info({t})").fetchall()
    for c in cols:
        print(' ',c[1],c[2])
