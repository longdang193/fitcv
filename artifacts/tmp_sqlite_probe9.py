import sqlite3, json, pprint
con=sqlite3.connect('data/fitcv_cp.sqlite3')
cur=con.cursor(); run='c8d06315-c2c4-4fd3-b432-18dc15cbc9b5'
cur.execute("SELECT run_json FROM local_pipeline_runs WHERE run_id=?",(run,))
rj=json.loads(cur.fetchone()[0])
cvdbg=json.loads(rj.get('cv_generation_debug_json') or '{}')
for rec in cvdbg.get('debug_records',[]):
    if rec.get('job_url')=='https://de.linkedin.com/jobs/view/founder-s-associate-m-f-d-at-docuply-4414307926?trk=public_jobs_topcard-title':
        print('keys',rec.keys())
        for k in ['validation_initial','validation_final','structured_cv_initial','structured_cv_final','runtime_provenance','repair_attempt','status']:
            v=rec.get(k)
            print('\n',k,':', type(v).__name__)
            print(str(v)[:1200])
        break
