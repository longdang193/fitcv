import sqlite3, json
run='be41f8a4-cf69-429f-8528-1477c6f2eeb1'
con=sqlite3.connect('data/fitcv_cp.sqlite3')
cur=con.cursor(); cur.execute("SELECT run_json FROM local_pipeline_runs WHERE run_id=?",(run,)); rj=json.loads(cur.fetchone()[0])
cvdbg=json.loads(rj.get('cv_generation_debug_json') or '{}')
for rec in cvdbg.get('debug_records',[]):
    if rec.get('status')=='validation_failed':
        print('JOB',rec.get('job_url'))
        print('repair',rec.get('repair_attempt'))
        print('failed_rule_ids',rec.get('failed_rule_ids'))
        print('first_failing_section_key',rec.get('first_failing_section_key'))
        print('operator_note',rec.get('operator_note'))
        vi=rec.get('validation_initial') or {}
        print('initial missing',vi.get('missing_sections'))
        print('initial grounding',vi.get('grounding_violations'))
        print('initial markdown blockers',vi.get('markdown_quality_blocking_issues'))
        print('---')
con.close()
