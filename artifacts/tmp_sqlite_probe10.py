import sqlite3, json
con=sqlite3.connect('data/fitcv_cp.sqlite3')
cur=con.cursor(); run='c8d06315-c2c4-4fd3-b432-18dc15cbc9b5'
cur.execute("SELECT run_json FROM local_pipeline_runs WHERE run_id=?",(run,))
rj=json.loads(cur.fetchone()[0])
cvdbg=json.loads(rj.get('cv_generation_debug_json') or '{}')
for rec in cvdbg.get('debug_records',[]):
    if rec.get('status')=='validation_failed':
        sec=((rec.get('structured_cv_initial') or {}).get('sections') or {})
        print('JOB',rec.get('job_url'))
        print('section_keys',list(sec.keys()))
        skills=sec.get('skills')
        print('skills_type',type(skills).__name__,'skills_preview',str(skills)[:260])
        print('enabled_sections',rec.get('enabled_sections'))
        print('missing', (rec.get('validation_initial') or {}).get('missing_sections'))
        print('---')
