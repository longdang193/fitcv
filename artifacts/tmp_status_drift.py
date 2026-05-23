import sqlite3, json
run='6778212e-2a1a-4dcd-9114-7cb0b51c8857'
con=sqlite3.connect('data/fitcv_cp.sqlite3'); cur=con.cursor(); cur.execute("SELECT run_json FROM local_pipeline_runs WHERE run_id=?",(run,)); rj=json.loads(cur.fetchone()[0])
cvdbg=json.loads(rj.get('cv_generation_debug_json') or '{}')
print('debug_records',len(cvdbg.get('debug_records',[])))
for rec in cvdbg.get('debug_records',[]):
    print(rec.get('job_url'),'->',rec.get('status'),rec.get('review_required_reason_code'))
con.close()
