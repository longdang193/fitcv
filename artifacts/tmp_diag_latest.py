import sqlite3, json
run='ebbea825-01b5-4a54-ade9-b2c9780398f2'
con=sqlite3.connect('data/fitcv_cp.sqlite3'); cur=con.cursor(); cur.execute("SELECT run_json FROM local_pipeline_runs WHERE run_id=?",(run,)); rj=json.loads(cur.fetchone()[0])
cvdbg=json.loads(rj.get('cv_generation_debug_json') or '{}')
for rec in cvdbg.get('debug_records',[]):
    print('\nJOB',rec.get('job_url'))
    print('status',rec.get('status'),'review',rec.get('review_required_reason_code'))
    print('validation_initial',rec.get('validation_initial'))
    print('validation_final',rec.get('validation_final'))
    print('error',rec.get('error'))
con.close()
