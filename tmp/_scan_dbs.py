import sqlite3, json, os, glob

# Check liveprobe DB
for db in glob.glob('tmp/**/*.sqlite3', recursive=True):
    print(f'\n=== DB: {db} ===')
    try:
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        print(f'Tables: {tables}')
        for t in tables:
            cur.execute(f"SELECT COUNT(*) FROM [{t}]")
            cnt = cur.fetchone()[0]
            if cnt > 0:
                print(f'  {t}: {cnt} rows')
                # Try to find the run
                try:
                    cur.execute(f"SELECT * FROM [{t}] WHERE CAST(* as TEXT) LIKE '%5ac8680c%' LIMIT 5")
                except:
                    pass
        conn.close()
    except Exception as e:
        print(f'  Error: {e}')
