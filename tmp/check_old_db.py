import sqlite3
p='data/fitcv_cp.sqlite3'
with sqlite3.connect(p) as c:
    tables=[r[0] for r in c.execute("select name from sqlite_master where type='table' order by name").fetchall()]
    print('tables', tables)
    for t in ('pipeline_runs','run_events','pipeline_settings'):
        try:
            n=c.execute(f'select count(*) from {t}').fetchone()[0]
            print(t, n)
        except Exception as e:
            print(t, 'err', e)
