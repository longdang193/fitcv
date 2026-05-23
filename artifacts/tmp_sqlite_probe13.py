import sqlite3, json
run='90c4fad7-2b4e-4bef-a9dc-558b53353f3a'
con=sqlite3.connect('data/fitcv_cp.sqlite3')
cur=con.cursor(); cur.execute("SELECT run_json FROM local_pipeline_runs WHERE run_id=?",(run,)); rj=json.loads(cur.fetchone()[0])
cvdbg=json.loads(rj.get('cv_generation_debug_json') or '{}')
for rec in cvdbg.get('debug_records',[]):
    if rec.get('status')=='validation_failed':
        tr=rec.get('runtime_provenance')
        live=rec.get('agentic_live_trace') or {}
        vs=live.get('validation_summary') or {}
        print('JOB',rec.get('job_url'))
        print('repair',rec.get('repair_attempt'))
        print('trace final missing',vs.get('final_missing_fields'))
        print('trace init missing',vs.get('initial_missing_fields'))
        print('trace final valid',vs.get('final_valid'))
        print('trace final issues',vs)
        print('----')
con.close()
