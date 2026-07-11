import sqlite3
from pathlib import Path
ids={'4d83ef03-4acc-4acd-8ea6-240127a21098','5656eb4d-34ec-4445-938d-f49ebadb8e14','84c1c6a2-4b5f-49d6-991c-b3197e94f1bb'}
files=[p for p in Path('.').rglob('*') if p.is_file() and p.suffix.lower() in {'.sqlite3','.sqlite','.db'}]
print('db files',len(files))
for p in files:
  try:
    con=sqlite3.connect(str(p))
    cur=con.cursor()
    tables=[r[0] for r in cur.execute("select name from sqlite_master where type='table'")]
    for t in ['local_pipeline_runs','pipeline_runs','runs']:
      if t in tables:
        q=f"select run_id from {t} where run_id in (?,?,?)"
        rows=[r[0] for r in cur.execute(q,tuple(ids)).fetchall()]
        if rows:
          print('FOUND',p,'table',t,'rows',rows)
  except Exception:
    pass
