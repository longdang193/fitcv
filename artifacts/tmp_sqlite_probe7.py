import sqlite3, json
con=sqlite3.connect('data/fitcv_cp.sqlite3')
cur=con.cursor(); run='c8d06315-c2c4-4fd3-b432-18dc15cbc9b5'
cur.execute("SELECT run_json FROM local_pipeline_runs WHERE run_id=?",(run,))
rj=json.loads(cur.fetchone()[0])
cvdbg_raw = rj.get('cv_generation_debug_json')
print(type(cvdbg_raw).__name__)
if isinstance(cvdbg_raw,str):
    print(cvdbg_raw[:300])
    try:
      parsed=json.loads(cvdbg_raw)
      print('parsed type',type(parsed).__name__,'len',len(parsed) if hasattr(parsed,'__len__') else 'na')
      print('item0 type',type(parsed[0]).__name__)
      print('item0 preview',str(parsed[0])[:200])
    except Exception as e:
      print('json error',e)
