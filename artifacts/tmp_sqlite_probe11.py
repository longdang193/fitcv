import sqlite3, json
run='90c4fad7-2b4e-4bef-a9dc-558b53353f3a'
con=sqlite3.connect('data/fitcv_cp.sqlite3')
cur=con.cursor(); cur.execute("SELECT run_json FROM local_pipeline_runs WHERE run_id=?",(run,)); rj=json.loads(cur.fetchone()[0])
cvdbg=json.loads(rj.get('cv_generation_debug_json') or '{}')
for rec in cvdbg.get('debug_records',[]):
    st=str(rec.get('status'))
    if st in {'validation_failed','generation_failed','accepted','review_required'}:
        vi=rec.get('validation_initial') or {}
        vf=rec.get('validation_final') or {}
        print('JOB',rec.get('job_url'))
        print('status',st,'repair',rec.get('repair_attempt'))
        print('init_missing',vi.get('missing_sections'),'final_missing',vf.get('missing_sections'))
        print('init_warn',vi.get('warnings'),'final_warn',vf.get('warnings'))
        print('error',rec.get('error'))
        print('-----')
con.close()
