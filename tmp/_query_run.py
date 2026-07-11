import sqlite3, json
conn = sqlite3.connect('data/fitcv_cp.sqlite3')
cur = conn.cursor()
cur.execute("SELECT run_id, created_at FROM local_pipeline_runs WHERE run_id = ?", ('5ac8680c-6cde-416d-9dcd-8c2064da2ba8',))
rows = cur.fetchall()
print(f'Found {len(rows)} matching runs')
for r in rows:
    print(r)
if rows:
    cur.execute("SELECT run_json FROM local_pipeline_runs WHERE run_id = ?", ('5ac8680c-6cde-416d-9dcd-8c2064da2ba8',))
    run_json = cur.fetchone()[0]
    data = json.loads(run_json)
    print(json.dumps(data, indent=2, default=str)[:5000])
    print('\n--- EVENTS ---')
    cur.execute("SELECT event_id, stage, level, message, created_at FROM local_pipeline_run_events WHERE run_id = ? ORDER BY created_at", ('5ac8680c-6cde-416d-9dcd-8c2064da2ba8',))
    for ev in cur.fetchall():
        print(ev)
