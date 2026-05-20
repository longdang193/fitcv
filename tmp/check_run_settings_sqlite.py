import sqlite3, json, glob
paths = glob.glob('data/*.db') + glob.glob('*.db') + glob.glob('data/**/*.db', recursive=True)
print('db_candidates', paths[:10])
db = None
for p in paths:
    conn = sqlite3.connect(p)
    cur = conn.cursor()
    try:
        cur.execute("select name from sqlite_master where type='table' and name='pipeline_runs'")
        if cur.fetchone():
            db = p
            conn.close()
            break
    except Exception:
        pass
    conn.close()
print('db', db)
if not db:
    raise SystemExit(1)
conn = sqlite3.connect(db)
cur = conn.cursor()
rid = 'e8cde832-a950-4d02-ba93-65ac0bafc3cc'
cur.execute('select effective_settings_json,status,error_message from pipeline_runs where run_id=?', (rid,))
row = cur.fetchone()
print('found', bool(row))
if row:
    eff, status, err = row
    print('status', status)
    print('err_head', (err or '')[:120])
    cfg = json.loads(eff or '{}')
    sm = cfg.get('synonym_management', {})
    print('synonym_management', {k: sm.get(k) for k in ['apply_to_run_enabled', 'promote_global_enabled', 'triage_recommendation_reuse_enabled']})
