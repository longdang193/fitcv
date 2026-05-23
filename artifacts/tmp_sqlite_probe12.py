import sqlite3, json
run='90c4fad7-2b4e-4bef-a9dc-558b53353f3a'
con=sqlite3.connect('data/fitcv_cp.sqlite3')
cur=con.cursor(); cur.execute("SELECT run_json FROM local_pipeline_runs WHERE run_id=?",(run,)); rj=json.loads(cur.fetchone()[0])
cvdbg=json.loads(rj.get('cv_generation_debug_json') or '{}')
for rec in cvdbg.get('debug_records',[]):
    if rec.get('status')=='validation_failed':
        print('JOB',rec.get('job_url'))
        v=rec.get('validation')
        print('validation keys', list((v or {}).keys()) if isinstance(v,dict) else type(v).__name__)
        print('validation', str(v)[:1500])
        print('structured final type', type(rec.get('structured_cv_final')).__name__)
        print('markdown_final len', len(rec.get('markdown_final') or ''))
        print('-----')
con.close()
