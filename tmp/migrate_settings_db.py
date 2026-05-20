import sqlite3, pathlib
old = pathlib.Path('data/fitcv_cp.sqlite3')
new = pathlib.Path('data/fitcv_cp_settings.sqlite3')
print('old exists', old.exists(), 'new exists', new.exists())
with sqlite3.connect(old) as c:
    rows = c.execute("select setting_key, setting_value_json, coalesce(updated_by,''), updated_at from pipeline_settings").fetchall()
print('old rows', len(rows))
new.parent.mkdir(parents=True, exist_ok=True)
with sqlite3.connect(new) as c:
    c.execute("""CREATE TABLE IF NOT EXISTS pipeline_settings (
        setting_key TEXT NOT NULL,
        setting_value_json TEXT NOT NULL,
        updated_by TEXT,
        updated_at TEXT NOT NULL
    )""")
    c.execute('DELETE FROM pipeline_settings')
    c.executemany('INSERT INTO pipeline_settings(setting_key, setting_value_json, updated_by, updated_at) VALUES (?, ?, ?, ?)', rows)
    c.commit()
    nn = c.execute('select count(*) from pipeline_settings').fetchone()[0]
print('new rows', nn)
