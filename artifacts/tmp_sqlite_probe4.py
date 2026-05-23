import sqlite3, json
con=sqlite3.connect('data/fitcv_cp.sqlite3')
cur=con.cursor(); run='c8d06315-c2c4-4fd3-b432-18dc15cbc9b5'
cur.execute("SELECT run_json FROM local_pipeline_runs WHERE run_id=?",(run,))
rj=json.loads(cur.fetchone()[0])
print('top keys',sorted(rj.keys()))
rr=rj.get('run_result') or {}
print('run_result keys',sorted(rr.keys()))
sta=((rr.get('stage_transition_artifacts') or {}).get('stages') or {})
print('stages keys',sorted(sta.keys()))
if 'cv_generation' in sta:
    cv=sta['cv_generation']
    print('cv_generation keys',sorted(cv.keys()))
    print('decision summary keys',sorted((cv.get('decision_summary') or {}).keys()))
    print('outputs_sample_len',len(cv.get('outputs_sample') or []))
    for i,s in enumerate((cv.get('outputs_sample') or [])[:5]):
        print('sample',i,'status',s.get('status'),'job',s.get('job_url'),'missing', (s.get('validation_final') or {}).get('missing_sections'),'warnings', (s.get('validation_final') or {}).get('warnings'))
con.close()
