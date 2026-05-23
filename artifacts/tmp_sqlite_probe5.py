import sqlite3, json
con=sqlite3.connect('data/fitcv_cp.sqlite3')
cur=con.cursor(); run='c8d06315-c2c4-4fd3-b432-18dc15cbc9b5'
cur.execute("SELECT cv_generation_debug_json, stage_transition_artifacts_json FROM local_pipeline_runs WHERE run_id=?",(run,))
cvdbg,staj = cur.fetchone()
records = json.loads(cvdbg) if cvdbg else []
print('cv_debug_records',len(records))
for rec in records:
    if str(rec.get('status'))=='validation_failed':
        vf = rec.get('validation_final') or {}
        print('JOB',rec.get('job_url'))
        print('missing_sections',vf.get('missing_sections'))
        print('warnings',vf.get('warnings'))
        print('required_sections',rec.get('enabled_sections'))
        print('error',rec.get('error'))
        print('----')
con.close()
