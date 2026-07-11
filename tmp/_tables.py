import sqlite3
for db in ['data/fitcv_cp.sqlite3','data/fitcv_cp.db']:
  con=sqlite3.connect(db)
  cur=con.cursor()
  tables=[r[0] for r in cur.execute("select name from sqlite_master where type='table' order by name")] 
  print('\nDB',db,'tables',len(tables))
  for t in tables[:80]:
    print(' ',t)
